import socket
import json
import struct
import hashlib
import os

HOST = "0.0.0.0"
PORT = 5001
CHUNK_DIR = "received_chunks"
BUFFER_SIZE = 4096
CHUNK_SIZE = 65536

os.makedirs(CHUNK_DIR, exist_ok=True)


def receive_exact(conn, size):
    data = b""

    while len(data) < size:
        part = conn.recv(min(BUFFER_SIZE, size - len(data)))

        if not part:
            raise ConnectionError("Connection closed unexpectedly")

        data += part

    return data


def receive_message(conn):
    header = receive_exact(conn, 4)
    length = struct.unpack("!I", header)[0]

    if length > 1024 * 1024:
        raise ValueError("Metadata message is too large")

    data = receive_exact(conn, length)
    return json.loads(data.decode("utf-8"))


def send_message(conn, message):
    data = json.dumps(message).encode("utf-8")
    conn.sendall(struct.pack("!I", len(data)) + data)


def reconstruct_file(backup_dir, filename, total_chunks):
    output_path = os.path.join(
        backup_dir, "reconstructed_" + filename
    )
    temporary_path = output_path + ".tmp"

    try:
        with open(temporary_path, "wb") as output:
            for chunk_id in range(total_chunks):
                chunk_path = os.path.join(
                    backup_dir, f"{filename}.chunk_{chunk_id}"
                )

                if not os.path.isfile(chunk_path):
                    print("Missing chunk:", chunk_id)
                    os.remove(temporary_path)
                    return None

                with open(chunk_path, "rb") as chunk:
                    while True:
                        block = chunk.read(BUFFER_SIZE)

                        if not block:
                            break

                        output.write(block)

        os.replace(temporary_path, output_path)

    except OSError:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise

    whole_hash = hashlib.sha256()

    with open(output_path, "rb") as file:
        while True:
            block = file.read(CHUNK_SIZE)

            if not block:
                break

            whole_hash.update(block)

    print("Reconstructed file:", output_path)
    print("Reconstructed SHA-256:", whole_hash.hexdigest())

    return output_path, whole_hash.hexdigest()


def handle_client(conn, address):
    print("Client connected:", address)

    backup_dir = None
    filename = None
    total_chunks = None
    expected_file_hash = None

    try:
        while True:
            metadata = receive_message(conn)

            if metadata.get("action") == "done":
                expected_file_hash = metadata.get("file_sha256")

                if not backup_dir or not filename or total_chunks is None:
                    send_message(conn, {
                        "status": "error",
                        "message": "No chunks were received"
                    })
                    break

                result = reconstruct_file(
                    backup_dir, filename, total_chunks
                )

                if result is None:
                    send_message(conn, {
                        "status": "error",
                        "message": "Reconstruction failed: missing chunks"
                    })
                    break

                reconstructed_path, actual_file_hash = result

                if not expected_file_hash:
                    send_message(conn, {
                        "status": "error",
                        "message": "Whole-file checksum was not supplied"
                    })
                    print("Whole-file SHA-256: NOT VERIFIED")
                    break

                if actual_file_hash != expected_file_hash:
                    print("Whole-file SHA-256: MISMATCH")
                    send_message(conn, {
                        "status": "error",
                        "message": "Whole-file checksum mismatch"
                    })
                    break

                print("Whole-file SHA-256: VERIFIED")

                send_message(conn, {
                    "status": "complete",
                    "message": "Transfer and whole-file checksum verified",
                    "file_sha256": actual_file_hash
                })
                break

            chunk_size = int(metadata["chunk_size"])
            chunk_id = int(metadata["chunk_id"])
            total_chunks = int(metadata["total_chunks"])
            backup_id = str(metadata["backup_id"])
            filename = os.path.basename(metadata["filename"])
            expected_chunk_hash = metadata["checksum"]

            if (
                not filename
                or filename in (".", "..")
                or not backup_id
                or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in backup_id)
                or total_chunks < 1
                or total_chunks > 1000000
                or chunk_id < 0
                or chunk_id >= total_chunks
                or chunk_size < 1
                or chunk_size > CHUNK_SIZE
            ):
                send_message(conn, {
                    "status": "error",
                    "message": "Invalid chunk metadata"
                })
                break

            backup_dir = os.path.join(CHUNK_DIR, backup_id)
            os.makedirs(backup_dir, exist_ok=True)

            chunk_data = receive_exact(conn, chunk_size)
            actual_chunk_hash = hashlib.sha256(chunk_data).hexdigest()

            if actual_chunk_hash != expected_chunk_hash:
                send_message(conn, {
                    "status": "error",
                    "message": "Chunk checksum mismatch",
                    "chunk_id": chunk_id
                })
                continue

            chunk_path = os.path.join(
                backup_dir, f"{filename}.chunk_{chunk_id}"
            )

            with open(chunk_path, "wb") as file:
                file.write(chunk_data)

            print(
                f"Saved chunk {chunk_id}: {filename} "
                f"({chunk_size} bytes)"
            )

            send_message(conn, {
                "status": "ok",
                "chunk_id": chunk_id,
                "checksum": actual_chunk_hash
            })

    except (
        ConnectionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        struct.error
    ) as error:
        print("Transfer error:", error)

    finally:
        conn.close()
        print("Client disconnected:", address)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        print(f"TCP backup server listening on port {PORT}")

        while True:
            conn, address = server.accept()
            handle_client(conn, address)


if __name__ == "__main__":
    main()













