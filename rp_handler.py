import runpod
from runpod.serverless.utils import rp_upload
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO
import websocket
import uuid
import tempfile
import socket
import traceback
from mutagen.mp4 import MP4

COMFY_DIR = "/workspace/comfywan"

# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 1000
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 900

# Enhanced WebSocket configuration for long-running jobs
WEBSOCKET_RECONNECT_ATTEMPTS = int(os.environ.get("WEBSOCKET_RECONNECT_ATTEMPTS", 100))
WEBSOCKET_RECONNECT_DELAY_S = int(os.environ.get("WEBSOCKET_RECONNECT_DELAY_S", 3))
WEBSOCKET_RECEIVE_TIMEOUT = int(os.environ.get("WEBSOCKET_RECEIVE_TIMEOUT", 30))  # seconds
MAX_EXECUTION_TIME = int(os.environ.get("MAX_EXECUTION_TIME", 1200))  # 20 minutes default

CALLBACK_API_ENDPOINT = os.environ.get("CALLBACK_API_ENDPOINT", "")
CALLBACK_API_SECRET = os.environ.get("CALLBACK_API_SECRET", "")

# Extra verbose websocket trace logs (set WEBSOCKET_TRACE=true to enable)
if os.environ.get("WEBSOCKET_TRACE", "false").lower() == "true":
    # This prints low-level frame information to stdout which is invaluable for diagnosing
    # protocol errors but can be noisy in production – therefore gated behind an env-var.
    websocket.enableTrace(True)

# Host where ComfyUI is running
COMFY_HOST = "127.0.0.1:3000"
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


def _comfy_server_status():
    """Return a dictionary with basic reachability info for the ComfyUI HTTP server."""
    try:
        resp = requests.get(f"http://{COMFY_HOST}/", timeout=5)
        return {
            "reachable": resp.status_code == 200,
            "status_code": resp.status_code,
        }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _attempt_websocket_reconnect(ws_url, max_attempts, delay_s, initial_error):
    """
    Attempts to reconnect to the WebSocket server after a disconnect.

    Args:
        ws_url (str): The WebSocket URL (including client_id).
        max_attempts (int): Maximum number of reconnection attempts.
        delay_s (int): Delay in seconds between attempts.
        initial_error (Exception): The error that triggered the reconnect attempt.

    Returns:
        websocket.WebSocket: The newly connected WebSocket object.

    Raises:
        websocket.WebSocketConnectionClosedException: If reconnection fails after all attempts.
    """
    print(f"worker-comfyui - Websocket connection closed unexpectedly: {initial_error}. Attempting to reconnect...")
    last_reconnect_error = initial_error

    for attempt in range(max_attempts):
        srv_status = _comfy_server_status()
        if not srv_status["reachable"]:
            # If ComfyUI itself is down there is no point in retrying the websocket –
            # bail out immediately so the caller gets a clear "ComfyUI crashed" error.
            print(
                f"worker-comfyui - ComfyUI HTTP unreachable – aborting websocket reconnect: {srv_status.get('error', 'status '+str(srv_status.get('status_code')))}"
            )
            raise websocket.WebSocketConnectionClosedException("ComfyUI HTTP unreachable during websocket reconnect")

        # Otherwise we proceed with reconnect attempts while server is up
        print(
            f"worker-comfyui - Reconnect attempt {attempt + 1}/{max_attempts}... (ComfyUI HTTP reachable, status {srv_status.get('status_code')})"
        )
        try:
            new_ws = websocket.WebSocket()
            new_ws.settimeout(WEBSOCKET_RECEIVE_TIMEOUT)  # Set receive timeout
            new_ws.connect(ws_url, timeout=10)
            print(f"worker-comfyui - Websocket reconnected successfully.")
            return new_ws
        except (
            websocket.WebSocketException,
            ConnectionRefusedError,
            socket.timeout,
            OSError,
        ) as reconn_err:
            last_reconnect_error = reconn_err
            print(f"worker-comfyui - Reconnect attempt {attempt + 1} failed: {reconn_err}")
            if attempt < max_attempts - 1:
                print(f"worker-comfyui - Waiting {delay_s} seconds before next attempt...")
                time.sleep(delay_s)
            else:
                print(f"worker-comfyui - Max reconnection attempts reached.")

    # If loop completes without returning, raise an exception
    print("worker-comfyui - Failed to reconnect websocket after connection closed.")
    raise websocket.WebSocketConnectionClosedException(
        f"Connection closed and failed to reconnect. Last error: {last_reconnect_error}"
    )


def validate_input(job_input):
    """Validates the input for the handler function."""
    if job_input is None:
        return None, "Please provide input"

    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Support for URL-based downloads with explicit fields
    input_img_url = job_input.get("input_img_url")
    input_img2_url = job_input.get("input_img2_url")
    input_vid_url = job_input.get("input_vid_url")

    return {
        "workflow": workflow,
        "input_img_url": input_img_url,
        "input_img2_url": input_img2_url,
        "input_vid_url": input_vid_url,
    }, None


def check_server(url, retries=500, delay=50):
    """Check if a server is reachable via HTTP GET request"""
    print(f"worker-comfyui - Checking API server at {url}...")
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"worker-comfyui - API is reachable")
                return True
        except (requests.Timeout, requests.RequestException):
            pass
        time.sleep(delay / 1000)

    print(f"worker-comfyui - Failed to connect to server at {url} after {retries} attempts.")
    return False


def download_file_from_url(url, timeout=60):
    """Download a file from URL and return its content."""
    print(f"worker-comfyui - Downloading file from URL: {url}")
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        content = BytesIO()
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content.write(chunk)
                total_size += len(chunk)

        content.seek(0)
        print(f"worker-comfyui - Downloaded {total_size / (1024*1024):.2f} MB from {url}")
        return content.getvalue()
    except Exception as e:
        print(f"worker-comfyui - Error downloading from {url}: {e}")
        raise


def upload_file_to_comfyui(filename, file_data):
    """Upload a file to ComfyUI server."""
    try:
        with open(f"{COMFY_DIR}/input/{filename}", 'wb') as f:
            f.write(file_data)
        return True
    except Exception as e:
        print(f"worker-comfyui - Error uploading {filename}: {e}")
        raise


def process_input_url(url_info, field_name):
    """Download and upload a single file from URL to ComfyUI."""
    if not url_info:
        return None

    try:
        # Handle both string URLs and dict objects
        if isinstance(url_info, str):
            url = url_info
            filename = os.path.basename(url)
        else:
            # Legacy dict format
            url = url_info.get("url")
            filename = url_info.get("filename")

        if not url or not filename:
            error_msg = f"Missing url or filename for {field_name}"
            print(f"worker-comfyui - {error_msg}")
            return {"status": "error", "message": error_msg}

        # Download file from URL
        file_data = download_file_from_url(url)

        # Upload to ComfyUI
        upload_file_to_comfyui(filename, file_data)

        print(f"worker-comfyui - Successfully processed {field_name}: {filename}")
        return {"status": "success", "filename": filename}

    except Exception as e:
        error_msg = f"Error processing {field_name}: {e}"
        print(f"worker-comfyui - {error_msg}")
        return {"status": "error", "message": error_msg}


def queue_workflow(workflow, client_id):
    """Queue a workflow to be processed by ComfyUI"""
    payload = {"prompt": workflow, "client_id": client_id}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    response = requests.post(f"http://{COMFY_HOST}/prompt", data=data, headers=headers, timeout=30)

    if response.status_code == 400:
        print(f"worker-comfyui - ComfyUI returned 400. Response body: {response.text}")
        try:
            error_data = response.json()
            error_message = "Workflow validation failed"

            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    error_message = error_info.get("message", error_message)
                else:
                    error_message = str(error_info)

            raise ValueError(f"{error_message}. Raw response: {response.text}")
        except (json.JSONDecodeError, KeyError):
            raise ValueError(f"ComfyUI validation failed (could not parse error response): {response.text}")

    response.raise_for_status()
    return response.json()


def get_history(prompt_id):
    """Retrieve the history of a given prompt using its ID"""
    response = requests.get(f"http://{COMFY_HOST}/history/{prompt_id}", timeout=30)
    response.raise_for_status()
    return response.json()


def get_image_data(filename, subfolder, image_type):
    """Fetch image bytes from the ComfyUI /view endpoint."""
    print(f"worker-comfyui - Fetching image data: type={image_type}, subfolder={subfolder}, filename={filename}")
    data = {"filename": filename, "subfolder": subfolder, "type": image_type}
    url_values = urllib.parse.urlencode(data)

    try:
        response = requests.get(f"http://{COMFY_HOST}/view?{url_values}", timeout=60)
        response.raise_for_status()
        print(f"worker-comfyui - Successfully fetched image data for {filename}")
        return response.content
    except Exception as e:
        print(f"worker-comfyui - Error fetching image data for {filename}: {e}")
        return None


def callback_api(payload):
    """Send callback to external API if configured"""
    if CALLBACK_API_ENDPOINT != "":
        try:
            headers = {"X-API-Key": f"{CALLBACK_API_SECRET}"}
            response = requests.post(CALLBACK_API_ENDPOINT, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"Failed to send log to API. Status code: {response.status_code}")
        except Exception as e:
            print(f"worker-comfyui - Error during callback: {e}")


def remove_mp4_metadata_item(file_path, metadata_key_to_remove):
    try:
        vid = MP4(file_path)
        if metadata_key_to_remove in vid.tags:
            del vid.tags[metadata_key_to_remove]
            vid.save()
            print(f"Metadata '{metadata_key_to_remove}' removed from {file_path}")
        else:
            print(f"Metadata '{metadata_key_to_remove}' not found in {file_path}")
    except Exception as e:
        print(f"Error removing metadata: {e}")


def file_handler(job_id, node_id, execution_time, file_info):
    """Handle file processing and upload"""
    filename = file_info.get("filename")
    subfolder = file_info.get("subfolder", "")
    img_type = file_info.get("type")

    if img_type == "temp":
        print(f"worker-comfyui - Skipping image {filename} because type is 'temp'")
        return None

    if not filename:
        print(f"worker-comfyui - Skipping image in node {node_id} due to missing filename: {file_info}")
        return None

    image_bytes = get_image_data(filename, subfolder, img_type)
    if not image_bytes:
        return None

    file_extension = os.path.splitext(filename)[1] or ".png"

    if os.environ.get("BUCKET_ENDPOINT_URL"):
        try:
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(image_bytes)
                temp_file_path = temp_file.name

            if file_extension == ".mp4":
                remove_mp4_metadata_item(temp_file_path, "©cmt")

            print(f"worker-comfyui - Uploading {filename} to S3...")
            s3_url = rp_upload.upload_image(job_id, temp_file_path)
            os.remove(temp_file_path)
            print(f"worker-comfyui - Uploaded {filename} to S3: {s3_url}")

            callback_api(
                {
                    "action": "s3_upload",
                    "job_id": job_id,
                    "filename": filename,
                    "data": s3_url,
                    "execution_time": execution_time,
                }
            )
            return {"filename": filename, "type": "s3_url", "data": s3_url}
        except Exception as e:
            print(f"worker-comfyui - Error uploading {filename} to S3: {e}")
            if "temp_file_path" in locals() and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as rm_err:
                    print(f"worker-comfyui - Error removing temp file {temp_file_path}: {rm_err}")
            return None
    else:
        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            return {"filename": filename, "type": "base64", "data": base64_image}
        except Exception as e:
            print(f"worker-comfyui - Error encoding {filename} to base64: {e}")
            return None


def handler(job):
    """
    Enhanced handler with better error handling and timeout management
    """
    job_input = job["input"]
    job_id = job["id"]

    # Input validation
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    workflow = validated_data["workflow"]
    input_img_url = validated_data.get("input_img_url")
    input_img2_url = validated_data.get("input_img2_url")
    input_vid_url = validated_data.get("input_vid_url")

    # Server availability check
    if not check_server(
        f"http://{COMFY_HOST}/",
        COMFY_API_AVAILABLE_MAX_RETRIES,
        COMFY_API_AVAILABLE_INTERVAL_MS,
    ):
        return {"error": f"ComfyUI server ({COMFY_HOST}) not reachable after multiple retries."}

    # Process input URLs (download and upload to ComfyUI)
    if input_img_url:
        result = process_input_url(input_img_url, "input_img_url")
        if result and result["status"] == "error":
            return {"error": result["message"]}

    if input_img2_url:
        result = process_input_url(input_img2_url, "input_img2_url")
        if result and result["status"] == "error":
            return {"error": result["message"]}

    if input_vid_url:
        result = process_input_url(input_vid_url, "input_vid_url")
        if result and result["status"] == "error":
            return {"error": result["message"]}

    ws = None
    client_id = str(uuid.uuid4())
    prompt_id = None
    output_data = []
    errors = []
    start_time = time.time()

    try:
        # Establish WebSocket connection
        ws_url = f"ws://{COMFY_HOST}/ws?clientId={client_id}"
        print(f"worker-comfyui - Connecting to websocket: {ws_url}")
        ws = websocket.WebSocket()
        ws.settimeout(WEBSOCKET_RECEIVE_TIMEOUT)  # Set receive timeout
        ws.connect(ws_url, timeout=10)
        print(f"worker-comfyui - Websocket connected")

        # Queue workflow
        try:
            queued_workflow = queue_workflow(workflow, client_id)
            prompt_id = queued_workflow.get("prompt_id")
            if not prompt_id:
                raise ValueError(f"Missing 'prompt_id' in queue response: {queued_workflow}")
            print(f"worker-comfyui - Queued workflow with ID: {prompt_id}")
            callback_api({"action": "in_queue", "job_id": job_id})
        except Exception as e:
            print(f"worker-comfyui - Error queuing workflow: {e}")
            if isinstance(e, ValueError):
                raise e
            else:
                raise ValueError(f"Unexpected error queuing workflow: {e}")

        # Enhanced execution monitoring with timeout
        print(f"worker-comfyui - Waiting for workflow execution ({prompt_id})...")
        execution_done = False
        last_progress_time = time.time()

        while True:
            current_time = time.time()

            # Check for overall timeout
            if current_time - start_time > MAX_EXECUTION_TIME:
                raise TimeoutError(f"Job execution exceeded maximum time limit of {MAX_EXECUTION_TIME} seconds")

            try:
                out = ws.recv()
                last_progress_time = current_time  # Reset progress timer on any message

                if isinstance(out, str):
                    message = json.loads(out)

                    if message.get("type") == "status":
                        status_data = message.get("data", {}).get("status", {})
                        queue_remaining = status_data.get("exec_info", {}).get("queue_remaining", "N/A")
                        print(f"worker-comfyui - Status update: {queue_remaining} items remaining in queue")

                    elif message.get("type") == "executing":
                        data = message.get("data", {})
                        if data.get("node") is None and data.get("prompt_id") == prompt_id:
                            print(f"worker-comfyui - Execution finished for prompt {prompt_id}")
                            execution_done = True
                            break
                        elif data.get("prompt_id") == prompt_id:
                            # Log progress for long-running jobs
                            node_id = data.get("node")
                            if node_id:
                                print(f"worker-comfyui - Executing node: {node_id}")

                    elif message.get("type") == "execution_error":
                        data = message.get("data", {})
                        if data.get("prompt_id") == prompt_id:
                            error_details = f"Node Type: {data.get('node_type')}, Node ID: {data.get('node_id')}, Message: {data.get('exception_message')}"
                            print(f"worker-comfyui - Execution error received: {error_details}")
                            errors.append(f"Workflow execution error: {error_details}")
                            break

                    elif message.get("type") == "progress":
                        data = message.get("data", {})
                        if data.get("prompt_id") == prompt_id:
                            value = data.get("value", 0)
                            max_val = data.get("max", 100)
                            node_id = data.get("node")
                            print(f"worker-comfyui - Progress: {value}/{max_val} (Node: {node_id})")

            except websocket.WebSocketTimeoutException:
                # More intelligent timeout handling
                elapsed = current_time - last_progress_time
                if elapsed > 120:  # 2 minutes without any message
                    print(f"worker-comfyui - No messages received for {elapsed:.1f}s, checking server status...")
                    srv_status = _comfy_server_status()
                    if not srv_status["reachable"]:
                        raise ConnectionError("ComfyUI server became unreachable during execution")
                print(
                    f"worker-comfyui - Websocket receive timed out. Still waiting... (elapsed: {current_time - start_time:.1f}s)"
                )
                continue

            except websocket.WebSocketConnectionClosedException as closed_err:
                try:
                    ws = _attempt_websocket_reconnect(
                        ws_url,
                        WEBSOCKET_RECONNECT_ATTEMPTS,
                        WEBSOCKET_RECONNECT_DELAY_S,
                        closed_err,
                    )
                    print("worker-comfyui - Resuming message listening after successful reconnect.")
                    continue
                except websocket.WebSocketConnectionClosedException as reconn_failed_err:
                    raise reconn_failed_err

            except json.JSONDecodeError:
                print(f"worker-comfyui - Received invalid JSON message via websocket.")
                continue

        if not execution_done and not errors:
            raise ValueError("Workflow monitoring loop exited without confirmation of completion or error.")

        # Process results
        print(f"worker-comfyui - Fetching history for prompt {prompt_id}...")
        history = get_history(prompt_id)

        if prompt_id not in history:
            error_msg = f"Prompt ID {prompt_id} not found in history after execution."
            print(f"worker-comfyui - {error_msg}")
            if not errors:
                return {"error": error_msg}
            else:
                errors.append(error_msg)
                return {
                    "error": "Job processing failed, prompt ID not found in history.",
                    "details": errors,
                }

        prompt_history = history.get(prompt_id, {})
        prompt_status = prompt_history.get("status", {})
        outputs = prompt_history.get("outputs", {})

        if not outputs:
            warning_msg = f"No outputs found in history for prompt {prompt_id}."
            print(f"worker-comfyui - {warning_msg}")
            if not errors:
                errors.append(warning_msg)

        # Calculate execution time
        execution_time = 0
        if prompt_status.get("status_str") == "success":
            started_at = 0
            ended_at = 0
            for msg_id, msg_body in prompt_status.get("messages", []):
                if msg_id == "execution_start":
                    started_at = msg_body["timestamp"]
                if msg_id == "execution_success":
                    ended_at = msg_body["timestamp"]
            if started_at and ended_at:
                execution_time = (ended_at - started_at) / 1000

        # Process outputs
        print(f"worker-comfyui - Processing {len(outputs)} output nodes...")
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    processed_file = file_handler(job_id, node_id, execution_time, img_info)
                    if processed_file:
                        output_data.append(processed_file)
                    else:
                        warn_msg = f"Skipping image in node {node_id} due to missing filename: {img_info}"
                        errors.append(warn_msg)
            if "gifs" in node_output:
                for gif_info in node_output["gifs"]:
                    processed_file = file_handler(job_id, node_id, execution_time, gif_info)
                    if processed_file:
                        output_data.append(processed_file)
                    else:
                        warn_msg = f"Skipping image in node {node_id} due to missing filename: {gif_info}"
                        errors.append(warn_msg)

            # Handle other output types
            other_keys = [k for k in node_output.keys() if k not in ["images", "gifs"]]
            if other_keys:
                warn_msg = f"Node {node_id} produced unhandled output keys: {other_keys}."
                print(f"worker-comfyui - WARNING: {warn_msg}")

    except TimeoutError as e:
        print(f"worker-comfyui - Timeout Error: {e}")
        return {"error": str(e)}
    except websocket.WebSocketException as e:
        print(f"worker-comfyui - WebSocket Error: {e}")
        print(traceback.format_exc())
        return {"error": f"WebSocket communication error: {e}"}
    except requests.RequestException as e:
        print(f"worker-comfyui - HTTP Request Error: {e}")
        print(traceback.format_exc())
        return {"error": f"HTTP communication error with ComfyUI: {e}"}
    except ValueError as e:
        print(f"worker-comfyui - Value Error: {e}")
        print(traceback.format_exc())
        return {"error": str(e)}
    except Exception as e:
        print(f"worker-comfyui - Unexpected Handler Error: {e}")
        print(traceback.format_exc())
        return {"error": f"An unexpected error occurred: {e}"}
    finally:
        if ws and hasattr(ws, "connected") and ws.connected:
            print(f"worker-comfyui - Closing websocket connection.")
            ws.close()

    # Prepare final result
    final_result = {}
    if output_data:
        final_result["images"] = output_data

    if errors:
        final_result["errors"] = errors
        print(f"worker-comfyui - Job completed with errors/warnings: {errors}")
        callback_api({"action": "error", "job_id": job_id, "errors": errors})

    if not output_data and errors:
        print(f"worker-comfyui - Job failed with no output images.")
        return {"error": "Job processing failed", "details": errors}
    elif not output_data and not errors:
        print(f"worker-comfyui - Job completed successfully, but the workflow produced no images.")
        final_result["status"] = "success_no_images"
        final_result["images"] = []

    print(f"worker-comfyui - Job completed. Returning {len(output_data)} image(s).")
    callback_api({"action": "complete", "job_id": job_id, "result": final_result})
    return final_result


if __name__ == "__main__":
    print("worker-comfyui - Starting handler...")
    runpod.serverless.start({"handler": handler})
