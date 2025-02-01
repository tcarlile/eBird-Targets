from bs4 import BeautifulSoup
import requests, configparser, csv, xlsxwriter
import pandas as pd
import numpy as np

def getMdVal(soup):
	'''
	Expects
		soup: A BeautifulSoup object of the eBird login page
	Returns
		mdval: A string of containing the login 'execution' parameter 
	'''
	mdlog = soup.find_all('input')
	# Loop through input tags, probably a better way to do this, but
	# this was faster than troubleshooting the error
	for i in mdlog:
		try:
			if i['name'] == 'execution':
				mdval = i['value']
		except:
			pass
			
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
	hsurl = 'https://ebird.org/targets?' + \
			'&r1=' + hs + \
			'&bmo=' + bmo + \
			'&emo=' + emo + \
			'&r2=' + reg + \
			'&t2=' + list
	return hsurl

def parseTargets(session, hs, targets):
	'''
	Expects:
		session: A logged in eBird requests session
		hs: An eBird Hotspot ID, found in hotsot URL, (e.g. L2284561)
		targets: A list of lists
	Returns:
		targets: An expanded list with parsed targets data table appended as lines
			data includes [index, species name, frequency, eBird species URL]		
	'''
	
	targURL = buildTargetsURL(hs, cfg['bmo'], cfg['emo'], cfg['reg'], cfg['list'])
	hotspot = session.get(targURL) #load hotspots target page
	soup = BeautifulSoup(hotspot.text, 'html.parser') 
	
	# Parse hotspot name
	name = soup.find('div', {'id' : 'targets-results' }).find('div', {'class' : 'SectionHeading-heading' }).find_all('strong')[1].getText()
	print('Parsing '+name)
	# We only want to parse native & naturalized and provisional
	labels = ['native-and-naturalized', 'exotic-provisional']
	# Iterate through categories
	for label in labels:
		for section in soup.find_all('section', {'aria-labelledby' : label } ): #probably a better way to find this
			# Iterate through species
			for target in section.find_all('li'):
				indx = target.find('div', {'class' : 'ResultsStats-index'} ).getText().strip().strip('.')
				spuh = target.find('div', {'class' : 'SpecimenHeader'} )
				urls = 'https://ebird.org'+spuh.find('a', href=True).get('href')
				urls = urls[:urls.rfind('/')]
				spuh = spuh.getText().strip()
				freq = target.find('span', {'class' : 'Heading'} ).getText().strip().strip('.%')
				targets.append([indx,spuh,freq,urls,name])
	return targets, name

def writeExcel(df):
	'''
	'''

	df = df.round(decimals=1)
	
	writer = pd.ExcelWriter(cfg['filebase']+'_targets.xlsx', engine='xlsxwriter')
	import pandas.io.formats.excel
	pandas.io.formats.excel.header_style = None
	name = cfg['filebase']+' Targets'
	df.to_excel(writer, sheet_name=name)
	
	workbook = writer.book
	worksheet = writer.sheets[name]
	ncol, nrow = worksheet.dim_colmax, worksheet.dim_rowmax
	
	#Setting up formatting of data
	gry = workbook.add_format({"bg_color": "#D0D0D0", "font_color": "#D0D0D0"})
	red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
	ylw = workbook.add_format({"bg_color": "#FCEAA6", "font_color": "#935A1D"})
	blu = workbook.add_format({"bg_color": "#ACC8E9", "font_color": "#1F3D61"})
	grn = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': '<',
										'value': cfg['cutoff'], 'format': gry})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': cfg['cutoff'], 'maximum' : 10, 'format': red})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 10, 'maximum' : 25, 'format': ylw})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': 'between',
										'minimum': 25, 'maximum' : 50, 'format': blu})
	worksheet.conditional_format(1, 1, nrow, ncol-1, {'type': 'cell', 'criteria': '>=',
													'value': 50, 'format': grn})
	data_format = workbook.add_format({'border': 1, 'bold': True, 'font_size': 14 })
	worksheet.set_column(1, ncol, 15, cell_format=data_format)

	# Format header row in really annoying way because of pandas enforces header formats
	hs_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
									'align': 'center', 'border': 1, 'font_size': 15 })
	for i, value in enumerate(df.columns.values):
		worksheet.write(0, i + 1, value, hs_format)
	
	# Format indexes row in really annoying way because of pandas enforces formats
	sp_format = workbook.add_format({'bold': True, 'align': 'right', 'border': 1, 'font_size': 15 })
	for i, (idx, row) in enumerate(df.iterrows()):
		worksheet.write(i+1, 0 , idx, sp_format)
	
	worksheet.set_column('A:A', 40)
	worksheet.set_row(0, 80)
	writer.close()

def main():
	
	# Read config file & hotspot file
	global cfg
	config = configparser.RawConfigParser()
	config.read('ebird.cfg')
	cfg = dict(config.items('ebird-config'))
	with open(cfg['hotspots']) as f:
		hotspots = [line.strip() for line in f]
	
	# eBird login URL
	login = 'https://secure.birds.cornell.edu/cassso/login?service=https%3A%2F%2Febird.org%2Flogin%2Fcas%3Fportal%3Debird&locale=en'
	with requests.session() as session: # Open session
		response = session.get(login) # Load logon page
		mdval = getMdVal(BeautifulSoup(response.text, 'html.parser')) #Get hidden data package
		# Data package for logon
		# If you're interested in how your password is used cfg['pw'] is the 
		# variable to look for, it's only sent to the eBird login website in the 
		# session.post command below 
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
			hs_names.append(name)
				
	#Create longform dataframe, and do some formatting
	targets_df = pd.DataFrame(targets, columns=['Rank', 'Species', 'Frequency', 'URL', 'Hotspot'])
	targets_df.drop(labels=['Rank'], axis=1, inplace=True)
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
			f.write('<div><a href=\"'+row[0]+'\">'+i+'</a></div>\n')
	
	writeExcel(targets_df)
	targets_df.to_csv(cfg['filebase']+'_targets.csv')
        		
if __name__ == '__main__':
	main()
