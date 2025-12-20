🦅 MERGEN: The Cyberdeck Command Center
"Every forgotten command is lost time. Mergen is your decentralized, AI-powered second brain designed for hackers."

Mergen is a next-generation command management system developed for cybersecurity experts and system administrators. Featuring CLI, GUI, and TUI interfaces, it supports end-to-end encrypted synchronization.

Write complex nmap, ffmpeg, or kubectl commands once; Mergen masks them, stores them, and beams them to all your devices (PC & Mobile) instantly.

🌟 Key Features
🛡️ Paranoid Security (OpSec First)
Auto-Masking: Sensitive data within commands—such as Passwords, API Keys, and IP Addresses (IPv4)—is automatically masked (e.g., <SECRET_KEY_1> or <SECRET_IP_0>) before saving to the database.

XSS & Injection Protection: All inputs undergo HTML Escaping and are isolated via SQL parameters.

Stealth Mode: Disable AI analysis with a single click to operate in an "Air-Gapped" logic.

🧠 Local + AI Hybrid Structure
Offline First: Your database is local and runs instantly, even without an internet connection.

Gemini AI Integration: Analyzes what your saved commands do or converts natural language questions (e.g., "What is the quietest nmap scan?") into executable commands.

📱 Decentralized Mobile Ops (Termux + Syncthing)
No Central Server. No Cloud.

P2P Encrypted Sync: Data synchronization via Syncthing.

Secure Tunneling: Access your home machine from anywhere in the world using Tailscale.

Pocket Cyberdeck: Turn your phone into a Cyberdeck using the TUI (Terminal User Interface) running natively on Android (Termux).

🏗️ Architecture
Mergen utilizes a "Decentralized Hybrid Cloud" architecture:

Kod snippet'i

graph TD
    A[KALI LINUX (Base Station)] -- Syncthing (P2P Sync) --> B((Data Pool));
    C[ANDROID / TERMUX (Field Ops)] -- Syncthing (P2P Sync) --> B;
    
    A -- Tailscale (VPN) --> C;
    
    subgraph "Mergen Core"
    D[SQLite DB]
    E[Python Backend]
    F[AI Engine (Optional)]
    end
🚀 Installation
1. Linux (Kali/Ubuntu/Debian) - Master Machine
Bash

# Clone the repository
git clone https://github.com/mes41c/mergen.git
cd mergen

# Start the installation wizard
python3 mergen.py --setup
The wizard will install necessary libraries (PyQt6, google-genai) and register the mergen command to your system path.

2. Android (Termux) - Mobile Operations
Mobile installation uses a specific method to bypass Android's security restrictions.

Prerequisites:
Install Termux and Syncthing applications on your phone.

Set up Syncthing synchronization between your PC and Phone (Recommended folder: ~/Download/Mergen).

Ensure mergen.py and mergen.db files have synced to the phone.

Termux Settings:
Bash

# Update and install dependencies
pkg update && pkg upgrade
pkg install python rust binutils build-essential clang

# AI Library (Compilation may take time)
pip install google-genai

# Grant storage permissions
termux-setup-storage
Mergen Installation (Wrapper):
Bash

# Navigate to the synced folder (Adjust path if necessary)
cd /storage/emulated/0/Download/Mergen

# Initialize setup
python mergen.py --setup

# Create a Wrapper to bypass Android "noexec" restriction
# (Paste this entire command at once)
echo 'python /storage/emulated/0/Download/Mergen/mergen.py "$@"' > $PREFIX/bin/mergen && chmod +x $PREFIX/bin/mergen
💻 Usage Guide
1. Graphical Interface (GUI) - Desktop
Bash

mergen --ui
Dashboard: Filter and edit all commands.

Import History: Select .zsh_history or .bash_history files from your pentest machines for bulk analysis.

AI Analysis: Use the "My Profile" button to analyze your competency based on command usage.

2. Terminal Interface (TUI) - Mobile & SSH
Bash

mergen --tui
No Mouse Needed: Full control via keyboard.

Hacker Aesthetic: Colorized interface designed for readability.

Search: Press / to search using Regex support.

3. Quick Command (CLI)
Bash

# Ask a question, get a command
mergen "scan all ports but evade the firewall"

# Import a history file directly from the terminal
mergen --import-history /path/to/.zsh_history
⚙️ Configuration & Security
Settings are stored in ~/.mergen_config.json.

API Key: Your Google Gemini API key is stored using base64-based obfuscation.

AI Toggle: You can cut all external data traffic by unchecking the "🤖 AI" box on the GUI.

⚠️ Legal Disclaimer
This tool is designed to increase the operational efficiency of cybersecurity professionals. The user is solely responsible for any illegal use of the commands obtained or stored using this tool.

<p align="center"> <sub>Developed by <b>MES</b> | "Code is Poetry, Security is Art."</sub> </p>
