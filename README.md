# SummonersWarMaster
SummonersWarMaster

Local Summoners War data tracker powered by a sidecar build of SW-Exporter
.




Getting Started (Repo + Submodules)
Prerequisites:

    Git (Windows/macOS/Linux)
    Node.js 18+ (for SW-Exporter)
    Python 3.10+ for most scripts


Setup

clone the repo:

    git clone --recurse-submodules https://github.com/vangoghvapor/SummonersWarMaster.git


get node:

    winget install OpenJS.NodeJS.LTS

    *this will prompt for admin rights
    ( or download from https://nodejs.org/ )

update submodules:

    cd SummonersWarMaster
    git submodule update --init --recursive

setup python:

    pip install -r requirements.txt


setup Win-Divert:
    run

    scripts\run_swex.cmd
After:

    the sw-exporter window should open,

If this is your first time running it:

        copy the absolute path of data/swex/exports
        open settings in sw-exporter and set Export / Output Directory to that path
        enable all plugins except delete before quitting, livesync, and merge sealed
        click Start Proxy at the top
        Steam option
        click Get Cert after it succeeds in starting the proxy
        click Get & Install Cert (Steam)
        click through any prompts to install the cert
        Stop the proxy server

NOW:

        Start Proxy Server

*** now Run SummonersWar on steam***

Logging in should generate the needed files
check data/swex/exports to see if json files are being created


***Run UI***

    run

    scripts\rune_viewer.py
    
    logs need to have been generated first for this to work

***


Main repo: https://github.com/vangoghvapor/SummonersWarMaster

SW-Exporter fork: https://github.com/vangoghvapor/sw-exporter-swmaster


