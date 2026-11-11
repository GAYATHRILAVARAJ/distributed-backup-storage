Distributed Backup System Using TCP and SDN
1. Project Overview
The Distributed Backup System is designed to securely transfer and store files across multiple backup servers using TCP communication and Software-Defined Networking (SDN).

The system divides files into smaller chunks, distributes them across two backup servers, verifies data integrity using SHA-256 checksums, and supports interrupted-transfer recovery.

An SDN controller dynamically selects between primary and backup network paths. When a link failure is detected, the controller updates the OpenFlow forwarding rules to use the alternate path.

2. System Architecture
The Mininet topology consists of:

h1 – Client (10.0.0.1)
h2 – Backup Server 1 (10.0.0.2)
h3 – Backup Server 2 (10.0.0.3)
s1, s2, s3, s4 – OpenFlow switches
c0 – Remote SDN controller
Primary path:

h1 → s1 → s2 → s4 → h2/h3

Backup path:

h1 → s1 → s3 → s4 → h2/h3

The controller communicates with the switches using OpenFlow 1.3 over port 6653.

3. Project Modules
client.py – Splits files into chunks, distributes them across backup servers, manages transfer metadata, resumes interrupted transfers, retrieves chunks and reconstructs files.
server.py – Implements TCP backup storage servers. Receives, verifies, stores and serves file chunks.
controller.py – Implements the OS-Ken SDN controller, monitors link status and installs forwarding rules for primary and backup paths.
topology.py – Creates the Mininet network with three hosts, four switches and two alternative paths.
storage_manager.py – Provides manifest management, chunk registration, integrity checking, reconstruction and selective chunk repair utilities.
test_metadata.py – Tests backup manifest creation and chunk registration.
test_reconstruction.py – Tests file reconstruction and checksum verification.
test_recovery.py – Tests detection of missing and corrupted chunks.
test_selective_recovery.py – Tests selective chunk repair and reconstruction.
performance_results.txt – Stores measured primary-path and backup-path performance results.
Note: The storage_manager.py module is tested independently using local storage directories. The live TCP client/server workflow maintains its own network-transfer manifest and chunk-handling logic.

4. Technologies Used
Python 3
TCP sockets
Mininet
Open vSwitch
OpenFlow 1.3
OS-Ken SDN controller
SHA-256
JSON metadata
Linux/Ubuntu
5. Network Configuration
Component	Configuration
Client	10.0.0.1
Backup Server 1	10.0.0.2
Backup Server 2	10.0.0.3
TCP port	5001
SDN controller port	6653
OpenFlow version	1.3
Chunk size	65,536 bytes
Primary path	s1–s2–s4
Backup path	s1–s3–s4
6. Implementation Features
TCP File Transfer
The client communicates with backup servers using TCP sockets. JSON metadata is transmitted with a four-byte length prefix, followed by binary chunk data when required.

File Chunking and Distribution
Input files are divided into chunks of 65,536 bytes. Chunks are distributed alternately between the two backup servers.

Data Integrity
Each chunk is verified using SHA-256. The reconstructed file is also checked against the original whole-file SHA-256 checksum.

Interrupted-Transfer Recovery
The client maintains a backup manifest and checks the chunks already stored on the servers. When the same backup ID is reused, valid existing chunks are skipped and missing chunks are transferred again.

File Reconstruction
The client retrieves chunks from the available backup servers in the correct order and reconstructs the original file.

SDN-Based Path Selection
The OS-Ken controller installs OpenFlow forwarding rules for the primary path. It monitors switch port-status events and changes forwarding rules when a primary-path link fails.

Network Failure Recovery
When the primary link between s1 and s2 is disabled, the controller selects the backup route through s3. When the primary link is restored, the controller selects the primary route again.

7. How to Execute the Project
Step 1: Start the SDN Controller
Open a terminal:

cd ~/tcp_file_transfer
source ~/distributed-backup/osken-venv/bin/activate
osken-manager controller.py
Keep this terminal running.

Step 2: Start the Mininet Topology
Open another terminal:

cd ~/tcp_file_transfer
sudo python3 topology.py
Wait until the Mininet prompt appears.

Step 3: Start Backup Server 1
At the Mininet prompt:

h2 python3 /home/gayathri-lavaraj/tcp_file_transfer/server.py --server-id server_1 --storage /home/gayathri-lavaraj/tcp_file_transfer/received_chunks/server_1 > /tmp/server1.log 2>&1 &
Step 4: Start Backup Server 2
h3 python3 /home/gayathri-lavaraj/tcp_file_transfer/server.py --server-id server_2 --storage /home/gayathri-lavaraj/tcp_file_transfer/received_chunks/server_2 > /tmp/server2.log 2>&1 &
Step 5: Verify Network Connectivity
net
pingall
Step 6: Transfer a File
h1 cd /home/gayathri-lavaraj/tcp_file_transfer && python3 client.py --file sample.txt --backup-id final_demo_001 --output-dir recovered_files
The client distributes chunks, verifies their integrity, retrieves them and reconstructs the original file.

8. Failure Simulation
Disable the primary path:

link s1 s2 down
The controller detects the failure and selects the backup path.

Inspect the forwarding rules:

sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s3
sh ovs-ofctl -O OpenFlow13 dump-flows s4
Restore the primary path:

link s1 s2 up
The controller selects the primary path after both link endpoints are available.

9. Testing
The project was tested for:

Small and large file transfers.
Distribution of chunks across two backup servers.
SHA-256 chunk and whole-file verification.
Interrupted-transfer recovery.
Missing and corrupted chunk detection.
Selective chunk repair.
File reconstruction.
Primary and backup SDN path selection.
OpenFlow forwarding-rule changes.
Network connectivity using pingall.
Performance comparison between primary and backup paths.
The included storage-manager test scripts verify metadata management, reconstruction, recovery detection and selective recovery.

10. Performance Evaluation
A 32 MiB test file was used for the primary-path and backup-path measurements.

Metric	Primary Path	Backup Path
File size	32 MiB	32 MiB
Number of chunks	512	512
Transfer time	87.1920 s	139.8647 s
Throughput	0.367 MiB/s	0.229 MiB/s
Reconstruction time	87.8805 s	141.4745 s
SHA-256 verification	Passed	Passed
The backup-path test took approximately 60.4% longer than the primary-path test.

Both reconstructed files passed whole-file SHA-256 verification.

These measurements represent one clean run per path and are reported as observed results.

11. Conclusion
The Distributed Backup System demonstrates TCP-based file transfer, distributed chunk storage, integrity verification, interrupted-transfer recovery and SDN-based network path selection.

The Mininet topology provides two alternative network paths. The OS-Ken controller detects link failures and updates OpenFlow forwarding rules to use the backup path.

The project was tested through file-transfer experiments, recovery tests, network connectivity checks, flow-table inspection and performance measurements.
