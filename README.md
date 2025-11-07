# 🐦 eBird-Targets 🐦
I wrote this script to help prepare for a birding trip to South & West Texas. Several others had shared eBird trip reports, which while incredibly helpful, were difficult to browse systematically. I wanted to synthesize some of this information to 1) find target species to study, 2) plan daily trip agendas, and 3) inform decision making on the fly in the field. A trip to Costa Rica prompted a rewrite to streamline code and eliminate most manual steps.

You'll need to do some research first. I can't automate that part! Primarily this is figuring out what hotspots you're interested in. eBird hotspots map and other birders are helpful for this bit. Once you have a list of hotspots, you're ready to go. The script will summarize the target species across hotspots of interest.

## Highlights
Starting with a text file containing eBird Hotspot (or region) IDs of interest and a configuration file, this script will: 
- Logon to your eBird account, load the targets page for each hotspot, & parse the targets data
- Combine hotspot targets tables into a single taxonomically sorted Species x Hotspot table
- Output an excel sheet with the Species x Hotspot table, color coded by frequency
- Output a crude "Study Guide." At the moment, just an HTML file with links to eBird species accounts

## Details & Caveats
A few notes about the output:
- The script parses anything that shows up on your eBird life list, so both "Native & Naturalized" and "Exotic: Provisional" species are listed in the output.
- The excel file contains a column of species frequencies for each hotspot, a ```Max Freq``` column with the maximum frequencies across parsed hotspots, and a ```Tax Sort``` column that allows you to easily re-sort taxonomically if you play around with the data.
- The color code should be fairly intutive:
  - Grey: < cutoff
  - Red: cutoff - 10%
  - Yellow: 10 - 25%
  - Blue: 25 - 50%
  - Green: >50%
- The "Study Guide" is just an unformatted html file with a taxonomically sorted list of links to eBird species accounts.
  
Some important notes, caveats, and limitations:
- The script reads your eBird password from the config file stored in plain text on your computer.
  - If you're paranoid you should remove the password from ```ebird.cfg``` after running the script.
  - The password is stored in the ```cfg['pw']``` variable (see lines ```120-121```, and is only sent to the eBird login page (see lines ```126-139```. Examine the code before running.
- Long staying and heavily twitched rarities can lead to spurious/unlikely targets. There were several of these for my Texas and Arizona trips. I suspect it's more of an issue in places that get tons of rarities. You may want to do a bit of data cleaning if something looks unlikely. Examples:
  - A Surbird seen on South Padre Island for ~1.5 weeks in April 2023 showed up at ~9.9% frequency in the output for my Texas trip.
  - One might also think that the seldom birded Boston Area bike path near me would be a great place to see a wintertime Townsed's Warlber (66.5%!).
- There are some things I haven't tested. If you do, please let me know:
  - HTML parsing when eBird is set to display both common and scientific names. 
  - When config and hotspots files have Windows line endings. I think pyhton3 handles this automatically, but I haven't explicitly tested.
- Currently this only supports English Common names, because that's what's in the taxonomy file. If there are taxonomy files with names in other languages those may work.

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
emo = 12
reg = world
list = life
cutoff = 1.5
taxonomy = eBird-Clements_v2025-integrated-checklist-October-2025.csv
taxsort = sort v2025
speccol = English name
```

- ```user = ``` Your eBird username
- ```pw = ``` Your eBird password
- ```hotspots = ``` A text file containing eBird hotspot IDs of interest. You can find the hotspot ID in the hotspot's eBird URL. For example the URL for the Mount Auburn Cemetery hotspot is ```https://ebird.org/hotspot/L207391```. The hotspot ID is ```L207391```. See an example file below.
- ```filebase = ``` A prefix for the script's output files. If you're preparing for a trip to Costa Rica you might use a prefix of ```CostaRica```
- ```bmo = ``` The beginning month of your time period of interest. Acceptable vales are ```1 - 12```
- ```emo = ``` The ending month of your time period of interest. Acceptable vales are ```1 - 12```
- ```reg = ``` The region list you want targets for. ```world``` specifies targets for your world list. Other options are the hotspot ID or region ID. 
- ```list = ``` The list you want targets for, options are: ```life```, ```year```, ```month```, ```day```	 
- ```cutoff = ``` A percent cutoff for filtering data. A cutoff of ```1.5``` means that if a species doesn't have a frequency of >= 1.5% in at least one of the hotspots, it will be filtered from the output data.
- ```taxonomy = ``` The filename for the current Clements/eBird taxonomy csv file. For example, from Oct 2025 to Oct 2026 this would be ```eBird-Clements_v2025-integrated-checklist-October-2025.csv```.
- ```taxsort = ``` The column header in the taxonomy csv file that specifies the taxonomic sort order (e.g. ```sort v2024```)
- ```speccol = ``` The column header in the taxonomy csv file that specifies the species name (e.g. ```English name```)

An example hotspots file from my Costa Rica trip. Each hotspot ID should be on its own line. The  top to bottom order of hotspots specifies the left to right order of columns in the output spreadsheet. I used colum ordering to organize in some way that makes sense for the trip. The file can have any name that you want, as long as it's specified in the ```ebird.cfg``` file:
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
eBird's yearly taxonomy update will require downloading the latest version of the Clements/eBird checklist and changing a couple of lines in the cfg file. I won't host these here, but will try to keep these links up to date.

The 2025 taxonomy downloads page, and a direct link to the relevant 2024 taxonomy file are below.
- [2025 Taxonomy Download Page](https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2025/2025-citation-checklist-downloads/)
- [2025 Clements/eBird csv](https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2025/10/eBird-Clements_v2025-integrated-checklist-October-2025.csv)

Updates to the eBird website will require more significant updates. eBird's 2024 style update required rewriting the code that parses the targets table HTML. Hopefully, the current eBird style will be stable for a few years.

## Dependencies
This script requires python3 with pandas, numpy, BeautifulSoup, requests, csv, and xlsxwriter. The versions I'm using are listed below. It's unlikely that this exact configuration is needed, but earlier versions of *some* packages might not work.
- python3 [3.9.12]
- pandas [1.4.2]
- numpy [1.21.5]
- bs4 [4.11.1]
- requests [2.27.1]
- csv [1.0]
- xlsxwriter [3.0.3]
