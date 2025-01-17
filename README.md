# eBird-Targets
The first version of this script was written to help prepare for an eleven day birding trip to South and West Texas. Several other birders had shared their eBird trip reports with me, which while incredibly helpful, were difficult to synthesize. This script was written to help create something digestible that would allow me 1) to find target species to study, 2) to help plan daily trip agendas, and 3) inform decision making on the fly in the field. A trip to Costa Rica prompted a rewrite to streamline the code and eliminate as many manual steps as possible.

You'll need to do some research first. I can't automate that part! Primarily this is figuring out  hotspots that you're interested in visiting. The eBird hotspots map, and other birders are helpful for this bit. Once you have a list of hotspots, you're ready to go. The script will output a table with the frequencies of target species across your hotspots of interest.

## Highlights
Starting with a text file containing eBird Hotspot (or region) IDs of interest and a configuration file, this script will: 
- Logon to your eBird account, load the targets page for each hotspot, & parse the data table
- Combine the hotspot targets tables into a taxonomically sorted Species x Hotspot table
- Output an excel sheet with the Species x Hotspot table, color coded by frequency
- Output a "Study Guide." At the moment, just an HTML file with links to eBird species accounts

## Details & Caveats
List of things that might be worth mentioning
- password stuff
- Hotspot order These should be ordered in the order in which you would like them to app
- Parses anything that shows up on your eBird Lofe List, so both "Native & Naturalized" & 
"Exotic: Provisional" species will be listed in the output.
- Color key: gray < cutoff, red cutoff - 10%, yellow 10-25%, blue 25-50%, green >50%
- Rarities: long staying rarities can yield spurious targets. e.g. Surfbird on south padre island (look up deets)
- languages, only english at the moment
- have not tested with windows line endings only linux/mac

## Usage
This script is run in the terminal with the command ```python3 targets_parser.py```. It should be run in a directory containing an ```ebird.cfg``` file, a file of hotspots of interest, and the Clements/eBird taxonomy csv file (see below for details).

All relevant parameters are passed to the script in a configuration file that must be named ```ebird.cfg```. The format for each parameter passed to the script is ```parameter = value```. The text to the left of the ```=``` should not be changed. See an example config file below, followed by a description of each parameter:

```
[ebird-config]
user = YourUserName
pw = YourPassword
hotspots = hotspots.txt
filebase = YourDestination
bmo = 1
emo = 1
reg = world
list = life
cutoff = 1.5
taxonomy = eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv
taxsort = sort v2024
speccol = English name
```

- ```user = ``` Your eBird username
- ```pw = ``` Your eBird password
- ```hotspots = ``` A text file containing eBird hotspot IDs of interest. You can find the hotspot ID in the hotspot's eBird URL. For example the web address for the Mount Auburn Cemetery hotspot is ```https://ebird.org/hotspot/L207391```, and the hotspot ID is ```L207391```. See an example file below.
- ```filebase = ``` A prefix for the script's output files. For example, if you're preparing for a trip to Costa Rica you might use a prefix of ```CostaRica```
- ```bmo = ``` The beginning month of your time period of interest. Acceptable vales are ```1 - 12```
- ```emo = ``` The ending month of your time period of interest. Acceptable vales are ```1 - 12```
- ```reg = ``` The region list you want targets for. ```world``` specifies targets for your world life list. Other options are the hotspot ID or region ID. 
- ```list = ``` The list you want targets for, options are: ```life```, ```year```, ```month```, ```day```	 
- ```cutoff = ``` A percent cutoff for filtering data. A cutoff of ```1.5``` means that if a species doesn't have a frequency of >= 1.5% in at least one of the hotspots, it will be filtered from the output data.
- ```taxonomy = ``` The filename for the current Clements/eBird taxonomy csv file. For example, from Oct 2024 to Oct 2025 this would be ```eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv```.
- ```taxsort = ``` The column header in the taxonomy csv file that specifies the taxonomic sort order (e.g. ```sort v2024```)
- ```speccol = ``` The column header in the taxonomy csv file that specifies the species name (e.g. ```English name```)

An example hotspots file from my Costa Rica trip. Each hotspot ID should be on its own line. The file can have any name that you want, as long as it's specified in the ```ebird.cfg``` file:
```
L2284561
L447854
L7086691
L487975
L30207900
L444121
L448041
```

## Updates
eBird's yearly taxonomy update will require downloading the latest version of the Clements/eBird checklist, and changing a couple of lines in the configuration file. I won't host these here, but will try to keep these links up to date.

The 2024 taxonomy downloads page, and a direct link to the relevant 2024 taxonomy file are below.
- https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2024/2024-citation-checklist-downloads/
- https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2024/10/eBird-Clements-v2024-integrated-checklist-October-2024-rev.csv

Updates to the eBird website will require more significant changes to the code. eBird's 2024 style update required rewriting the code to parse the targets table HTML. Hopefully, the current eBird style will be stable for awhile.

## Dependencies
This script requires python3 with pandas, numpy, BeautifulSoup, requests, csv, and xlsxwriter. The versions I'm using are listed below. It's unlikely that this exact configuration is needed, but earlier versions of *some* packages might not work.
- python3 [3.9.12]
- pandas [1.4.2]
- numpy [1.21.5]
- bs4 [4.11.1]
- requests [2.27.1]
- csv [1.0]
- xlsxwriter [3.0.3]
