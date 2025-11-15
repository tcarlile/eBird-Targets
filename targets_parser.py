from bs4 import BeautifulSoup
import time, requests, configparser, csv, xlsxwriter
import pandas as pd

def getConfig(fn):
	'''
	Expects:
		fn: A string specifying the config filename
	Returns:
		cfg: a dict of ebird.cfg parameters
	'''
	# Read config file & hotspot file
	config = configparser.RawConfigParser()
	config.read(fn) # !!!Reads your password here!!!
	cfg = dict(config.items('ebird-config')) # !!!Stores password in cfg['pw'] varaible!!!
	return cfg # !!!Returns cfg varaible to main()!!!

def getHotspots(fn):
	'''
	Expects:
		fn: A string specifying the hotspots filename
	Returns:
		cfg: a dict of ebird.cfg parameters
	'''
	with open(fn) as f:
		hotspots = [line.strip() for line in f]
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

def readTaxonomy(cfg):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
	Returns:
		taxonomy: a pandas df containing a cleaned version of the taxonomy file
	'''
	# Import & clean Clements /eBird taxonomy
	taxonomy = pd.read_csv(cfg['taxonomy'])
	taxonomy = taxonomy[[cfg['taxsort'], cfg['speccol']]] # Subset to sort column and species name column
	taxonomy.drop_duplicates(subset=[cfg['speccol']], inplace=True)
	taxonomy = taxonomy[taxonomy[cfg['speccol']].notna()]
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

	df.to_csv(cfg['filebase']+'_targets.csv') # Write to CSV first
	
	writer = pd.ExcelWriter(cfg['filebase']+'_targets.xlsx', engine='xlsxwriter') # Create excel file
	name = cfg['filebase']+' Targets' # Sheet name
	df = df.round(decimals=1)
	df.to_excel(writer, sheet_name=name) # Write data
	
	# Get workbook, worksheet, and dimensions for formatting
	workbook = writer.book
	worksheet = writer.sheets[name]
	ncol, nrow = worksheet.dim_colmax, worksheet.dim_rowmax

	# Formatting cells below cutoff
	gry = workbook.add_format({"bg_color": "#D0D0D0", "font_color": "#D0D0D0"})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': '<',
										'value': cfg['cutoff'], 'format': gry})
	# Formatting cells between cutoff & 10%
	red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': cfg['cutoff'], 'maximum' : 10, 'format': red})
	# Formatting cells between 10 & 25%
	ylw = workbook.add_format({"bg_color": "#FCEAA6", "font_color": "#935A1D"})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 10, 'maximum' : 25, 'format': ylw})
	# Formatting cells between 25 & 50%
	blu = workbook.add_format({"bg_color": "#ACC8E9", "font_color": "#1F3D61"})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 25, 'maximum' : 50, 'format': blu})
	# Formatting cells > 50%
	grn = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
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
	# May be a better way, but want to maintain compatibility with multiple pd vers
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
	with open(cfg['filebase']+'_study_guide.html', 'w') as f:
		f.write('<!DOCTYPE html>\n<html>\n<head>\n<title>eBird Study Guide</title>\n</head>\n')
		for i, row in df.iterrows():
			f.write('<div><a href=\"'+row.iloc[0]+'\">'+i+'</a></div>\n')
	
def main():
	
	cfg = getConfig('ebird.cfg') # !!!Read config file, your password is read here. See function above !!!
	hotspots = getHotspots(cfg['hotspots']) # Read hotspots file
	session = ebirdLogin(cfg) # !!!Login to eBird, your password is used to login to eBird. See function above!!!
	del cfg['pw'] # !!!Delete your password from cfg so you don't have to look through code for rest of subfunctions!!!
	hs_names, targets = parseHotspots(cfg, session, hotspots) # Visits hotspot targets pages and parses data
	session.close()

	taxonomy = readTaxonomy(cfg) # Read taxonomy csv used by eBird
	targ_df, url_df = processTargData(cfg, targets, hs_names, taxonomy) # Use pandas to wrangle data into tables for output
	writeExcel(cfg, targ_df)
	writeURLs(cfg, url_df)
        		
if __name__ == '__main__':
	main()
