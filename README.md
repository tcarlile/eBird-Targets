# eBird-Targets
The first version of this script was written to help me prepare for an eleven day birding trip to South and West Texas. Several other birders had shared their eBird trip reports with me. These reports were incredibly helpful, but synthesizing everything was difficult. This script was written to help create something digestible that would allow me to focus on study species and to help in planning daily trip agendas, and in decision making on the fly while out in the field. A trip to Costa Rica prompted a rewrite to streamline and eliminate as many manual steps as possible.

You'll need to do some research first, I can't automate this part! Primarily this is the hotspots that you're interested in visiting, but there are other considerations. The eBird hotspots map, and other birders are helpful for this bit. Once you have a list of hotspots, you're ready to go. The script will output a table of frequencies of target species across your hotspots of interest.

## Highlights
Starting with a text file containing eBird Hotspot (or region) IDs of interest and a configuration file, this script will: 
- Logon to your eBird account, load the targets page for each hotspot, & parse the targets table
- Combine the hotspot targets tables into a taxonomically sorted table: Species x Hotspot
- Output an excel sheet of the Species x Hotspot table, color coded by frequency
- Output a "Study Guide" for targets, just an HTML file with links to eBird species account pages

## Updates
eBird's yearly taxonomy update will necessitate downloading the latest version of the Clements/eBird checklist, and changing a couple of lines in the configuration file. I won't host these here, but will try to keep these links up to date. 

The 2024 taxonomy downloads page, and a direct link to the relevant 2024 taxonomy file are below.
- https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2024/2024-citation-checklist-downloads/
- https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2024/10/eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv

eBird website, and style updates will require more significant updates. eBird's 2024 style update required an update to the code that parses the targets table HTML. Hopefully, this will be stable for awhile.
  
## Details
(Native & Naturalized & Exotic: Provisional)

## Usage

## Dependencies
This script requires python3 with pandas, numpy, BeautifulSoup, requests, csv, and xlsxwriter. The versions I'm using are listed below, but it's unlikely that you will need the exact versions I'm using.
- python3 [3.9.12]
- pandas [1.4.2]
- numpy [1.21.5]
- bs4 [4.11.1]
- requests [2.27.1]
- csv [1.0]
- xlsxwriter [3.0.3]
