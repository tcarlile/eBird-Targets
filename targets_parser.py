from bs4 import BeautifulSoup
import time, requests, configparser, csv, xlsxwriter
import pandas as pd

def getConfig(fn):
	'''
	Expects:
		fn: A string specifying the config filename
	Returns:
		cfg: a dict of config file parameters
	'''
	# Read config file & hotspot file
	global cfg
	config = configparser.RawConfigParser()
	config.read(fn)
	cfg = dict(config.items('ebird-config'))
	return cfg

def getHotspots(fn):
	'''
	Expects:
		fn: A string specifying the hotspots filename
	Returns:
		cfg: a dict of config file parameters
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

def buildTargetsURL(hs, bmo, emo, reg, list):
	'''
	Expects: elements of an eBird targets page URL, all str()
		hs: eBird Hotspot ID (Or Region ID)
		bmo, Beginning month of target period (1-12)
		emo, Ending month of target period (1-12)
		reg, Region for target list: "life" or hotspot ID/region ID
		list, target period for list, "life", "year", "month", "day"	
	Returns:
		hsurl: an eBird targets page URL	
	
	'''
	hsurl = 'https://ebird.org/targets?' + '&r1=' + hs + \
			'&bmo=' + bmo + '&emo=' + emo + '&r2=' + reg + '&t2=' + list
	return hsurl

def parseTargets(session, hs, targets):
	'''
	Expects:
		session: A logged in eBird requests session
		hs: An eBird Hotspot ID, found in hotsot URL, (e.g. L2284561)
		targets: A list of lists
	Returns:
		targets: An expanded list with parsed targets data table appended as lines
			data includes [species name, frequency, eBird species URL]		
	'''
	
	targURL = buildTargetsURL(hs, cfg['bmo'], cfg['emo'], cfg['reg'], cfg['list'])
	hotspot = session.get(targURL) # Load hotspots target page
	soup = BeautifulSoup(hotspot.text, 'html.parser')
	targLen = len(targets) # Length of targets list before parsing hotspot
	
	name = soup.find('option', {'value' : hs }).getText() # Parse hotspot name from region selection box
	for label in ['native-and-naturalized', 'exotic-provisional']: # Only parse what eBird includes in life list
		for section in soup.find_all('section', {'aria-labelledby' : label } ):
			for target in section.find_all('li'): # Find all species, <li> element per spuh, iterate, parse
				elem = target.find('div', {'class' : 'SpecimenHeader'})
				if elem.find('em', {'class' : 'sci'}): # find() yields bs4.element.Tag if Common + Sci displayed
					elem.find('em', {'class' : 'sci'}).decompose() # Remove scientific name
				else: # If user has Common name displayed find() yields NoneType
					pass
				# Only psychopaths would use the Scientific name only setting, so I'm not going to deal with that
				urls = 'https://ebird.org/species/'+elem.find('a').get('data-species-code')
				spuh = elem.getText().strip()
				freq = target.find('div', {'class' : 'ResultsStats-stats'}).get('title').strip('.% frequency')
				targets.append([spuh,freq,urls,name])
	print('Parsed ' + name)
	time.sleep(4) # To limit rate of eBird page loads 
	if targLen == len(targets): # Occurs when target species data is empty
		name = None # Change hotspot name to None, used as check in main()
	return targets, name

def writeExcel(df):
	'''
	'''

	writer = pd.ExcelWriter(cfg['filebase']+'_targets.xlsx', engine='xlsxwriter') # Create excel file
	#TODO pass header=False
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

	# Format header row in really annoying way because pandas enforces header format
	hs_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
									'align': 'center', 'border': 1, 'font_size': 15 })
	# TODO REPLACE ITERATION WITH bulk format
	for i, value in enumerate(df.columns.values):
		worksheet.write(0, i + 1, value, hs_format)
	
	# Format indexes row in really annoying way because pandas enforces col1 formats
	sp_format = workbook.add_format({'bold': True, 'align': 'right', 'border': 1, 'font_size': 15 })
	for i, (idx, row) in enumerate(df.iterrows()):
		worksheet.write(i+1, 0 , idx, sp_format)
	
	# Size first row & first column
	worksheet.set_column('A:A', 40)
	worksheet.set_row(0, 80)
	writer.close()

def main():
	
	# Read config file & hotspot file
	cfg = getConfig('ebird.cfg') #Read Config File
	hotspots = getHotspots(cfg['hotspots'])

	# eBird login URL
	login = 'https://secure.birds.cornell.edu/cassso/login?service=https%3A%2F%2Febird.org%2Flogin%2Fcas%3Fportal%3Debird&locale=en'
	with requests.session() as session: # Open session
		response = session.get(login) # Load logon page
		mdval = getMdVal(BeautifulSoup(response.text, 'html.parser')) #Get hidden data package
		# Data package for logon
		# If you're interested in how your password is used cfg['pw'] is the variable of interest,
		# It's only sent to the eBird login website in the session.post command below
		data = {'locale' : 'en',
				'username' : cfg['user'],
				'password' : cfg['pw'],
				'rememberMe' : 'on',
				'execution' : mdval,
				'_eventId' : 'submit'} 
		r_post = session.post(login, data=data) # Submit login data
		
		hs_names, targets = [], [] # Init lists to store hotspot names & target data
		for hs in hotspots: # Iterate hotspots & scrape data
			targets, name = parseTargets(session, hs, targets)
			if name: # Don't add empty hotspots to the list
				hs_names.append(name)
				
	#Create longform dataframe, and do some formatting
	targets_df = pd.DataFrame(targets, columns=['Species', 'Frequency', 'URL', 'Hotspot'])
	targets_df['Frequency'] = pd.to_numeric(targets_df['Frequency'])
	
	#Create dataframe for storing URLS, will tweak a bit later
	url_df = targets_df.drop(labels=['Frequency','Hotspot'], axis=1)
	url_df.drop_duplicates(inplace=True)
	
	targets_df = targets_df.pivot(index='Species', columns='Hotspot', values='Frequency')
	targets_df = targets_df[hs_names] #Reorder columns
	targets_df.fillna(value=0, inplace=True) # replace NaNs
	targets_df['Max Freq'] = targets_df[hs_names].max(axis=1) # Get maximum freq
	targets_df = targets_df[targets_df['Max Freq'] >= float(cfg['cutoff'])]
	targets_df = targets_df.reset_index()
	
	# Import & clean Clements /eBird taxonomy
	taxonomy = pd.read_csv(cfg['taxonomy'])
	taxonomy = taxonomy[[cfg['taxsort'], cfg['speccol']]]
	taxonomy.drop_duplicates(subset=[cfg['speccol']], inplace=True)
	taxonomy = taxonomy[taxonomy[cfg['speccol']].notna()]
	
	# Incorporate taxonomy into targets, sort, clean
	targets_df['Tax Sort'] = targets_df['Species'].map(taxonomy.set_index([cfg['speccol']])[cfg['taxsort']])
	targets_df.sort_values(by='Tax Sort', inplace=True)
	targets_df.set_index('Species', inplace=True)
	
	# Sort URLs taxonomically
	url_df['Tax Sort'] = url_df['Species'].map(taxonomy.set_index([cfg['speccol']])[cfg['taxsort']])
	url_df.sort_values(by='Tax Sort', inplace=True)
	url_df.set_index('Species', inplace=True)
	
	#write urls to html file for study
	with open(cfg['filebase']+'_study_guide.html', 'w') as f:
		f.write('<!DOCTYPE html>\n<html>\n<head>\n<title>eBird Study Guide</title>\n</head>\n')
		for i, row in url_df.iterrows():
			f.write('<div><a href=\"'+row.iloc[0]+'\">'+i+'</a></div>\n')
	
	writeExcel(targets_df)
	targets_df.to_csv(cfg['filebase']+'_targets.csv')
        		
if __name__ == '__main__':
	main()
