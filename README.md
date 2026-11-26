# 🐦 eBird-Targets 🐦
I wrote this script to help prepare for a trip to South & West Texas. I had several eBird trip reports from other birders. While incredibly helpful, these were difficult to browse systematically. I wanted to synthesize some of this information to 1) find target species to study, 2) help plan daily agendas, and 3) inform on the fly decision making in the field. A trip to Costa Rica prompted a rewrite to streamline code and eliminate most manual steps.

You'll need to do some research first. Primarily this is figuring out what hotspots you're interested in. The eBird hotspots map and other birders are helpful for this bit. Once you have a list of hotspots, you're ready to go. The script will summarize target species across hotspots of interest.

## Highlights
Starting with a text file containing eBird Hotspot (or region) IDs of interest and a configuration file, this script will: 
- Logon to your eBird account, load the targets page for each hotspot, and parse the targets data
- Output an Excel file with a Species x Hotspot table, taxonomically sorted, and color coded by frequency
- Output a styled HTML "Study Guide" with links to eBird and Birdos of the World species accounts

## This Script Uses Your eBird Username and Password
Since eBird doesn't provide individual level API access, the script needs to login to your eBird account to get targets. As written, the script ***reads your eBird usename and password from the config file stored in plain text on your computer*** and uses these to log into ebird. I've tried to explicitly document where and how your password is used in the code (please take a look).
  - All lines where your password is read, stored, or used are commented as follow ```#!!!Description of password use!!!```
  - Your password is read from the config file in ```getConfig()```: line ```72```. Login credentials are extracted from the ```[login-config]``` section on lines ```107-109```. The function is called on line ```650```.
  - Your password is submitted to eBird in ```ebirdLogin()```: lines ```175``` and ```180```. The function is called on line ```668```.
  - Your username and password are deleted from the ```lgn``` variable after login succeeds (lines ```671-672```), before hotspot parsing begins.
  - If you're paranoid you should remove the password from ```ebird.cfg``` after running the script.

## Details
**A few notes about the output:**
- The script parses "eBird lifers", so both "Native & Naturalized" and "Exotic: Provisional" are included in the output.
- The Excel file contains:
  - A column of species frequencies for each hotspot
  - A ```MaxFreq``` column with the maximum frequency for each species across parsed hotspots
  - A ```TaxSort``` column that allows you to easily re-sort taxonomically
- The color code should be fairly intutive:
  - Grey: < cutoff
  - Red: cutoff - 10%
  - Yellow: 10 - 25%
  - Blue: 25 - 50%
  - Green: >50%
- The "Study Guide" is a styled HTML file with a taxonomically sorted list of links to eBird and Birds of the World species accounts.
  
**Some important notes, caveats, and limitations:**

- Long staying and heavily twitched rarities can lead to spurious/unlikely targets. There were several of these for my Texas and Arizona trips. I suspect it's more of an issue in places that get tons of rarities. You may want to do some data cleaning if something looks unlikely. Examples:
  - A Surbird seen on South Padre Island for ~1.5 weeks in April 2023 showed up at ~9.9% frequency in the output for my Texas trip.
  - One might also think that the seldom birded Boston Area bike path near me would be a great place to see a wintertime Townsed's Warlber (66.5%!).
- There are some things I haven't tested. If you do, please let me know:
  - When config and hotspots files have Windows line endings. I think pyhton3 handles this automatically, but I haven't explicitly tested.
- Currently this only supports English (United States) Common names, because that's what's in the taxonomy file. If there are taxonomy files with names in other languages those may work.

## Usage
This script is run in the terminal with the command ```python3 targets_parser.py```. It should be run in a directory containing an ```ebird.cfg``` file, a file of hotspots of interest, and the Clements/eBird taxonomy csv file.

All relevant parameters are passed to the script in a configuration file that must be named ```ebird.cfg```. The format for each parameter passed to the script is ```parameter = value```. The text to the left of the ```=``` should not be changed. See an example config file below, followed by a description of each parameter:

```
[ebird-config]
hotspots = hotspots.txt
filebase = CostaRica
bmo = 1
emo = 1
reg = world
list = life
cutoff = 1.5
taxonomy = eBird-Clements_v2026_integrated-checklist-October-2026.csv
taxonomy_sha256 = ca63a4c93fe20f1ea6d073e6ff929c3d1f0b0ed7592839ecfce1ef296237a331
taxsort = sort v2026
speccol = English name

[login-config]
user = YourUserName
pw = YourPassword
```

- ```hotspots = ``` A text file containing eBird hotspot or region IDs of interest. You can find the hotspot ID in the hotspot's eBird URL. For example the URL for the Mount Auburn Cemetery hotspot is ```https://ebird.org/hotspot/L207391```. The hotspot ID is ```L207391```. See an example file below. The URL for Cochise County, Arizona is ```https://ebird.org/region/US-AZ-003```. The rgion ID is ```US-AZ-003```.
- ```filebase = ``` A prefix for the script's output files. If you're preparing for a trip to Costa Rica you might use a prefix of ```CostaRica```
- ```bmo = ``` The beginning month of your time period of interest. Acceptable vales are ```1 - 12```
- ```emo = ``` The ending month of your time period of interest. Acceptable vales are ```1 - 12```
- ```reg = ``` The region list you want targets for. ```world``` specifies your world list. Other options are a country (e.g. ```US```), a state/province (e.g. ```US-MA```), or a county (e.g. ```US-MA-017```).
- ```list = ``` The list you want targets for, options are: ```life```, ```year```, ```month```, ```day```	 
- ```cutoff = ``` A percent cutoff for filtering data. A cutoff of ```1.5``` means that if a species doesn't have a frequency of >= 1.5% in at least one of the hotspots, it will be filtered from the output data.
- ```taxonomy = ``` The local filename for the Clements/eBird taxonomy CSV. Download the file from the link below and place it in the directory where you run the script.
- ```taxonomy_sha256 = ``` The expected 64-character SHA-256 checksum for the taxonomy CSV. The script verifies the local file before parsing it. I will keep this updated as the taxonomy is updated.
- ```taxsort = ``` The column header in the taxonomy csv file that specifies the taxonomic sort order (e.g. ```sort v2026```)
- ```speccol = ``` The column header in the taxonomy csv file that specifies the species name (e.g. ```English name```)
- ```user = ``` Your eBird username
- ```pw = ``` Your eBird password

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
eBird's yearly taxonomy update will require downloading the latest Clements/eBird checklist and changing the ```taxonomy``` filename, ```taxonomy_sha256```, and ```taxsort``` value in the cfg file (and Avibase from 2026 onward). I won't host these here, but will try to keep these links up to date.

The 2026 taxonomy downloads page, and a direct link to the relevant 2025 taxonomy file are below.
- [2026 Taxonomy Download Page](https://www.birds.cornell.edu/clementschecklist/introduction/updateindex/october-2025/2026-citation-checklist-downloads/)
- [2026 eBird/Clements csv](https://www.birds.cornell.edu/clementschecklist/wp-content/uploads/2026/11/eBird-Clements_v2026_integrated-checklist-October-2026.csv)

Updates to the eBird website will require more significant updates. eBird's 2024 style update required rewriting the code that parses the targets table HTML. Hopefully, the current eBird style will be stable for a few years.

## Dependencies
In addition to Python's standard library, this script requires these third-party packages:
- pandas
- beautifulsoup4 (imported as `bs4`)
- requests
- XlsxWriter

Install the pinned Python packages with `python -m pip install -r requirements.txt`.