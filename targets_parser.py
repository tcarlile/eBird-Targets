from calendar import month
from importlib.resources import path
from logging import config
from io import BytesIO
from typing import Union

from bs4 import BeautifulSoup
from pathlib import Path
import time, requests, configparser, csv, xlsxwriter, re, hashlib
import pandas as pd

def getConfig(fn: Union[str, Path]) -> tuple[dict, dict]:
	'''
	Expects:
		fn: A string specifying the config filename
	Returns:
		cfg: a dict of ebird.cfg parameters
		lgn: a dict of login credentials
	'''

	# Check if config file exists
	path = Path(fn)
	if not path.is_file():
		raise FileNotFoundError(f'Config file not found or is not a file: {path}')

	# Read config file
	config = configparser.RawConfigParser()
	with path.open(encoding='utf-8') as config_file:
		config.read_file(config_file, source=str(path)) # !!!Reads your password here!!!

	# Check if required sections exist
	if not config.has_section('ebird-config'):
		raise ValueError(f'Missing [ebird-config] section in {path}')
	if not config.has_section('login-config'):
		raise ValueError(f'Missing [login-config] section in {path}')

	# Get config parameters from ebird-config section
	cfg = dict(config.items('ebird-config'))

	# Check required values in ebird-config
	req_cfg = [ 'hotspots', 'filebase', 'bmo', 'emo', 'reg',
		'list', 'cutoff', 'taxonomy', 'taxonomy_sha256', 'taxsort', 'speccol']
	invalid_cfg = [key for key in req_cfg if not cfg.get(key, '').strip()]
	if invalid_cfg:
		raise ValueError(
			'Missing  empty values in [ebird-config]: {}'.format(
				', '.join(invalid_cfg)))

	if not re.fullmatch(r'[0-9a-fA-F]{64}', cfg['taxonomy_sha256']):
		raise ValueError(
			'[ebird-config] taxonomy_sha256 must be a 64-character hexadecimal SHA-256'
		)

	# Validate region code
	reg_patterns = (
		r'^[A-Z]{2}$',
		r'^[A-Z]{2}-[A-Z]{2,3}$',
		r'^[A-Z]{2}-[A-Z]{2,3}-[A-Z0-9]{3}$',
	)
	if cfg['reg'] != 'world' and not any(
		re.fullmatch(pattern, cfg['reg']) for pattern in reg_patterns
	):
		raise ValueError(
			'[ebird-config] reg must be world or a valid country/region code'
		)

	# Validate bmo and emo values are integers between 1 and 12
	for key in ('bmo', 'emo'):
		try:
			month = int(cfg[key])
		except ValueError as exc:
			raise ValueError(
				'[ebird-config] {} must be an integer from 1 to 12'.format(key)
			) from exc

		if not 1 <= month <= 12:
			raise ValueError(
				'[ebird-config] {} must be from 1 to 12'.format(key)
			)

	# Validate cutoff value is a float between 0 and 100
	try:
		cfg['cutoff'] = float(cfg['cutoff'])
	except ValueError as exc:
		raise ValueError(
			'[ebird-config] cutoff must be a number from 0 to 100'
		) from exc

	if not 0 <= cfg['cutoff'] <= 100:
		raise ValueError('[ebird-config] cutoff must be from 0 to 100')

	# Validate list value is one of the valid options
	valid_lists = ('life', 'year', 'month', 'day')
	if cfg['list'] not in valid_lists:
		raise ValueError(
			'[ebird-config] list must be one of: {}'.format(', '.join(valid_lists))
		)
	
	# Add filebase and outdir to cfg
	cfg['filebase'] = '{}_{}'.format(cfg['filebase'], cfg['list'])
	cfg['outdir'] = str(Path(cfg['filebase']))
	# Get login credentials from login-config section
	lgn = dict(config.items('login-config')) # !!!lgn dict contains login credentials!!!

	# Check if required keys exist in login-config section
	req_lgn = ['user', 'pw']
	invalid_lgn = [key for key in req_lgn if not lgn.get(key, '').strip()]
	if invalid_lgn:
		raise ValueError(
			'Missing or empty values in [login-config]: {}'.format(
				', '.join(invalid_lgn)
			)
		)

	return cfg, lgn # !!!Returns lgn variable to main()!!!

def getHotspots(fn: Union[str, Path]) -> list[str]:
	'''
	Expects:
		fn: The path to the hotspots file
	Returns:
		hotspots: unique hotspot IDs in order of first appearance
	'''
	# Check if hotspots file exists
	path = Path(fn)
	if not path.is_file():
		raise FileNotFoundError(f'Hotspots file not found or is not a file: {path}')

	# Read hotspots file and filter out comments and empty lines
	with open(path, encoding='utf-8') as f:
		lines = f.readlines()
		hotspots = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith('#')]
		hotspots = list(dict.fromkeys(hotspots))

	# Validate hotspot IDs against expected regex patterns
	patterns = (r'^L\d+$', r'^[A-Z]{2}$', r'^[A-Z]{2}-[A-Z]{2,3}$', 
	            r'^[A-Z]{2}-[A-Z]{2,3}-[A-Z0-9]{3}$')
	
	bad_hs = [hs for hs in hotspots if not any(re.fullmatch(p, hs) for p in patterns)]
	if bad_hs:
		raise ValueError(
			'Invalid hotspot or region ID(s) in {}: {}'.format(
				path, ', '.join(bad_hs)
			)
		)

	return hotspots
	
def getMdVal(soup):
	'''
	Expects
		soup: A BeautifulSoup object of the eBird login page
	Returns
		mdval: A string containing the hidden 'execution' parameter required for login
	'''
	mdlog = soup.find('input', {'name' : 'execution'}) # Find <input> tag with name execution
	mdval = mdlog['value'] # Get the value parameter 
	return mdval

def ebirdLogin(cfg):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
	Returns
		session: A session object logged ito your ebird account
	'''
	ebirdURL = 'https://secure.birds.cornell.edu/cassso/login?service=https%3A%2F%2Febird.org%2Flogin%2Fcas%3Fportal%3Debird&locale=en'

	session = requests.session()
	response = session.get(ebirdURL) # Load logon page
	mdval = getMdVal(BeautifulSoup(response.text, 'html.parser')) #Get hidden data package
	data = {'locale' : 'en',
			'username' : cfg['user'],
			'password' : cfg['pw'], # !!!Here's your Password!!!
			'rememberMe' : 'on',
			'execution' : mdval,
			'_eventId' : 'submit'} 
	r_post = session.post(ebirdURL, data=data) # !!!Here's where your password is used to log into eBird!!!
	return session

def parseHotspots(cfg, session, hotspots):
	''''
	Expects:
		cfg: a dict of ebird.cfg parameters
		session: A logged in eBird session object
		hotspots: A list f hotspot IDs
	Returns:
		hs_names: A list of hotspot names
		targets: A list with parsed targets data across hotspots
				data includes [species name, frequency, eBird species URL]	
	'''
	
	hs_names, targets = [], [] # Init lists to store hotspot names & target data
	for hs in hotspots: # Iterate hotspots & scrape data
		targets, name = parseTargets(cfg, session, hs, targets)
		if name: # Don't add empty hotspots to the list
			hs_names.append(name)
	return hs_names, targets

def parseTargets(cfg, session, hs, targets):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		session: A logged in eBird requests session
		hs: An eBird Hotspot ID, found in hotsot URL, (e.g. L2284561)
		targets: A list of lists
	Returns:
		targets: An expanded list with parsed targets data table appended as lines
			data includes [species name, frequency, eBird species URL]		
	'''
	
	targURL = 'https://ebird.org/targets?' + '&r1=' + hs + '&bmo=' + cfg['bmo'] + \
			'&emo=' + cfg['emo'] + '&r2=' + cfg['reg'] + '&t2=' + cfg['list'] # Build URL for targets page
	print(targURL)
	hotspot = session.get(targURL) # Load hotspots target page
	soup = BeautifulSoup(hotspot.text, 'html.parser') 
	
	targLen = len(targets) # Length of targets list before parsing hotspot
	name = soup.find('option', {'value' : hs }).getText() # Parse hotspot name from region selection box
	for label in ['native-and-naturalized', 'exotic-provisional']: # Only parse what eBird includes in life list
		for section in soup.find_all('section', {'aria-labelledby' : label } ):
			for target in section.find_all('li'): # Find all species, defined by <li> elements
				elem = target.find('div', {'class' : 'SpecimenHeader'}) # Species header
				if elem.find('em', {'class' : 'sci'}): # find() yields bs4.element.Tag if Common + Sci displayed
					elem.find('em', {'class' : 'sci'}).decompose() # Remove scientific name
				else: # If user has Common name displayed find() yields NoneType
					pass
				# Only psychopaths would use the Scientific name only setting, so I'm not going to deal with that
				urls = 'https://ebird.org/species/'+elem.find('a').get('data-species-code') # Get eBird species code
				spuh = elem.getText().strip() # Get species common name
				freq = target.find('div', {'class' : 'ResultsStats-stats'}).get('title').strip('.% frequency') # Get frequency
				targets.append([spuh,freq,urls,name])
	
	print('Parsed ' + name)
	time.sleep(4) # To limit rate of eBird page loads 
	if targLen == len(targets): # Occurs when target species data is empty
		name = None # Change hotspot name to None, used as check in parseHotspots()
	return targets, name

def readTaxonomy(cfg: dict) -> pd.DataFrame:
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
	Returns:
		taxonomy: a pandas df containing a cleaned version of the local taxonomy CSV
	'''

	# Check if taxonomy file exists and is a file
	taxonomy_path = Path(cfg['taxonomy'])
	if not taxonomy_path.is_file():
		raise FileNotFoundError(
			'Taxonomy file not found or is not a file: {}'.format(taxonomy_path)
		)

	# Read taxonomy file and verify SHA-256 checksum
	taxonomy_bytes = taxonomy_path.read_bytes()
	expected_sha256 = cfg['taxonomy_sha256'].lower()
	actual_sha256 = hashlib.sha256(taxonomy_bytes).hexdigest()
	if actual_sha256 != expected_sha256:
		raise ValueError(
			'Taxonomy SHA-256 mismatch for {}: expected {}, got {}'.format(
				taxonomy_path, expected_sha256, actual_sha256
			)
		)

	# Clean Clements /eBird taxonomy
	taxonomy = (
		pd.read_csv(BytesIO(taxonomy_bytes))
		.select([cfg['taxsort'], cfg['speccol']])
		.drop_duplicates(subset=[cfg['speccol']])
		.dropna(subset=[cfg['speccol']])
	)
	return taxonomy
	
def processTargData(cfg, targets, hs_names, taxonomy):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		targets: A list of lists
		hs_names: A list of hotspot names
		taxonomy: A pandas data frame parsed from the eBird taxonomy file
	Returns:
		targets_df: a pandas data frame of species x hotspot frequencies
		url_df: a pandas data frame of unique species URLS sorted taxonomically
	'''
	
	#Create longform dataframe, and do some formatting
	targets_df = pd.DataFrame(targets, columns=['Species', 'Frequency', 'URL', 'Hotspot'])
	targets_df['Frequency'] = pd.to_numeric(targets_df['Frequency'])
	
	#Create dataframe for storing URLS, will tweak a bit later
	url_df = targets_df.drop(labels=['Frequency','Hotspot'], axis=1)
	url_df.drop_duplicates(inplace=True)
	
	targets_df = targets_df.pivot(index='Species', columns='Hotspot', values='Frequency') # Pivot from logform to species x hotspot
	targets_df = targets_df[hs_names] #Reorder columns by ordered
	targets_df.fillna(value=0, inplace=True) # replace NaNs
	targets_df['Max Freq'] = targets_df[hs_names].max(axis=1) # Get maximum freq
	targets_df = targets_df[targets_df['Max Freq'] >= float(cfg['cutoff'])] # Filter species rows below cutoff
	targets_df = targets_df.reset_index()
	
	# Incorporate taxonomy into targets, sort, clean
	targets_df['Tax Sort'] = targets_df['Species'].map(taxonomy.set_index([cfg['speccol']])[cfg['taxsort']])
	targets_df.sort_values(by='Tax Sort', inplace=True)
	targets_df.set_index('Species', inplace=True)
	
	# Sort URLs taxonomically
	url_df['Tax Sort'] = url_df['Species'].map(taxonomy.set_index([cfg['speccol']])[cfg['taxsort']])
	url_df.sort_values(by='Tax Sort', inplace=True)
	url_df.set_index('Species', inplace=True)
	
	return targets_df, url_df
	
def writeExcel(cfg, df):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		df: a longform pandas data frame of ebird targets data
	Does:
		df is used to write an HTML file
	'''
	outdir = Path(cfg['outdir'])
	df.to_csv(outdir / f"{cfg['filebase']}_targets.csv") # Write to CSV first
	
	writer = pd.ExcelWriter(outdir / f"{cfg['filebase']}_targets.xlsx", engine='xlsxwriter') # Create excel file
	name = cfg['filebase']+' Targets' # Sheet name
	df = df.round(decimals=1)
	df.to_excel(writer, sheet_name=name) # Write data
	
	# Get workbook, worksheet, and dimensions for formatting
	workbook = writer.book
	worksheet = writer.sheets[name]
	ncol, nrow = worksheet.dim_colmax, worksheet.dim_rowmax

	# Formatting cells below cutoff
	gry = workbook.add_format({'bg_color': '#D0D0D0', 'font_color': '#D0D0D0'})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': '<',
										'value': cfg['cutoff'], 'format': gry})
	# Formatting cells between cutoff & 10%
	red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': cfg['cutoff'], 'maximum' : 10, 'format': red})
	# Formatting cells between 10 & 25%
	ylw = workbook.add_format({'bg_color': '#FCEAA6', 'font_color': '#935A1D'})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 10, 'maximum' : 25, 'format': ylw})
	# Formatting cells between 25 & 50%
	blu = workbook.add_format({'bg_color': '#ACC8E9', 'font_color': '#1F3D61'})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 25, 'maximum' : 50, 'format': blu})
	# Formatting cells > 50%
	grn = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': '>=',
													'value': 50, 'format': grn})
	
	# Cell formatting
	data_format = workbook.add_format({'border': 1, 'bold': True, 'font_size': 14 })
	worksheet.set_column(1, ncol, 15, cell_format=data_format)

	# Define hotspot & species formats
	hs_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
									'align': 'center', 'border': 1, 'font_size': 15 })
	sp_format = workbook.add_format({'bold': True, 'align': 'right', 'border': 1, 'font_size': 15 })

	# Write formats by rewriting original data into cells with formatting
	# Really annoying method, but is recommended in xlsxwriter docs
	# May be a better way, but want to maintain compatibility with multiple pd versions
	for i, value in enumerate(df.columns.values):
		worksheet.write(0, i + 1, value, hs_format)
	for i, (idx, row) in enumerate(df.iterrows()):
		worksheet.write(i+1, 0 , idx, sp_format)
	
	# Size first row & first column
	worksheet.set_column('A:A', 40)
	worksheet.set_row(0, 80)
	writer.close()

def writeURLs(cfg, df):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		df: a pandas dataframe of species URLs
	Does:
		df is written to excel and formatted
	'''
	outdir = Path(cfg['outdir'])
	with open(outdir / f"{cfg['filebase']}_study_guide.html", 'w') as f:
		f.write('<!DOCTYPE html>\n<html>\n<head>\n<title>eBird Study Guide</title>\n</head>\n')
		for i, row in df.iterrows():
			f.write('<div><a href=\"'+row.iloc[0]+'\">'+i+'</a></div>\n')
	
def main():
	
	cfg, lgn = getConfig('ebird.cfg') # !!!Read config file, your password is read here. See function above !!!
	Path(cfg['outdir']).mkdir(exist_ok=True)
	hotspots = getHotspots(cfg['hotspots']) # Read hotspots file
	session = ebirdLogin(lgn) # !!!Login to eBird, your password is used to login to eBird. See function above!!!
	del lgn['pw'] # !!!Delete your password from lgn so you don't have to look through code for rest of subfunctions!!!
	del lgn['user'] # !!!Delete your password from lgn so you don't have to look through code for rest of subfunctions!!!
	hs_names, targets = parseHotspots(cfg, session, hotspots) # Visits hotspot targets pages and parses data
	session.close()

	taxonomy = readTaxonomy(cfg) # Read taxonomy csv used by eBird
	targ_df, url_df = processTargData(cfg, targets, hs_names, taxonomy) # Use pandas to wrangle data into tables for output
	writeExcel(cfg, targ_df)
	writeURLs(cfg, url_df)
        		
if __name__ == '__main__':
	main()