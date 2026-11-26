import time, requests, configparser,  re, hashlib, html, calendar, bs4
from io import BytesIO
from pathlib import Path
from typing import Union
from bs4 import BeautifulSoup
import pandas as pd

def validateConfigs(cfg: dict, required_keys: list) -> None:
	'''
	Expects:
		cfg: a dict of configuration parameters
		required_keys: a list of keys that must be present in cfg
	Raises:
		ValueError: if any required key is missing or has an empty value
	'''
	
	for key in required_keys:
		if not cfg.get(key, '').strip():
			raise ValueError(f'Missing or empty value for key: {key}')

def regexValidator(param: str, patterns: tuple, message: str) -> None:
	'''
	Expects:
		param: a str
		patterns: a list of regex pattern strings
		message: Eror message to text
	Raises:
		ValueError: if param does not match a regex in pattern
	'''

	if not any(re.fullmatch(p, param) for p in patterns):
		raise ValueError(message)

def validateNumeric(param: str, name: str, fn: function, min: Union[int, float], 
                    max: Union [int, float]) -> None: 
	'''
	Expects:
		param: a str
		name: a str
		fn: a function, int or float specifically
		min: int or float, minimum acceptable value of fn(param)
		max: int or float, mmaximum acceptable value of fn(param)
	Raises:
		ValueError: if param does not match a regex in pattern
	'''
	
	try:
		convert = fn(param)
	except ValueError:
		raise ValueError(f'[ebird-config] {name} must be a/an {fn} between {min} and {max}')

	if not min <= convert <= max:
		raise ValueError(f'[ebird-config] {name} must be between {min} and {max}')

def getConfig(fn: Union[str, Path]) -> tuple[dict, dict]:
	'''
	Expects:
		fn: A string specifying the config filename
	Returns:
		cfg: a dict of ebird.cfg parameters
		lgn: a dict of login credentials
	'''

	# Check if config file exists
	config_path = Path(fn)
	if not config_path.is_file():
		raise FileNotFoundError(f'Config file not found or is not a file: {config_path}')

	# Read config file
	config = configparser.RawConfigParser()
	with config_path.open(encoding='utf-8') as config_file:
		config.read_file(config_file, source=str(config_path)) # !!!Reads your password here!!!

	# Check if required sections exist
	if not config.has_section('ebird-config'):
		raise ValueError(f'Missing [ebird-config] section in {config_path}')
	if not config.has_section('login-config'):
		raise ValueError(f'Missing [login-config] section in {config_path}')

	# Get and validate config parameters from ebird-config section
	cfg = dict(config.items('ebird-config'))
	validateConfigs(cfg, ['hotspots', 'filebase', 'bmo', 'emo', 'reg',
		'list', 'cutoff', 'taxonomy', 'taxonomy_sha256', 'taxsort', 'speccol'])

	# Validate text patterns
	sha256_pattern = [r'[0-9a-fA-F]{64}']
	regexValidator(cfg['taxonomy_sha256'], sha256_pattern,
	               '[ebird-config] taxonomy_sha256 must be a 64-character hexadecimal SHA-256')
	region_patterns = (r'^world$', r'^[A-Z]{2}$', r'^[A-Z]{2}-[A-Z]{2,3}$',
					r'^[A-Z]{2}-[A-Z]{2,3}-[A-Z0-9]{3}$')
	regexValidator(cfg['reg'], region_patterns,
	               '[ebird-config] reg must be world or a valid country/region code')
	list_patterns = (r'^life$', r'^year', r'^month', r'^day')
	regexValidator(cfg['list'], list_patterns,
				   '[ebird-config] list must be life, year, month, or day')

	#Validate numeric patterns
	validateNumeric(cfg['bmo'], 'bmo', int, 1, 12)
	validateNumeric(cfg['emo'], 'emo', int, 1, 12)
	validateNumeric(cfg['cutoff'], 'cutoff', float, 0, 100)

	# Rounding out cfg with final values
	cfg['cutoff'] = float(cfg['cutoff'])
	cfg['filebase'] = '{}_{}'.format(cfg['filebase'], cfg['list'])
	cfg['outdir'] = str(Path(cfg['filebase']))
	
	# Get and validate !!!login credentials!!! from login-config section
	lgn = dict(config.items('login-config')) 
	validateConfigs(lgn, ['user', 'pw'])
	
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
		hotspots = [line.strip() for line in f.readlines() if line.strip() and not line.lstrip().startswith('#')]
		hotspots = list(dict.fromkeys(hotspots)) # Remove duplicates

	# Validate Hotspot IDs
	hotspot_id_patterns = (r'^L\d+$', r'^[A-Z]{2}$', r'^[A-Z]{2}-[A-Z]{2,3}$', 
	            r'^[A-Z]{2}-[A-Z]{2,3}-[A-Z0-9]{3}$')
	for hs in hotspots:
		regexValidator(hs, hotspot_id_patterns, f'Invalid hotspot or region ID: {hs}')
	
	if len(hotspots) == 0:
		raise ValueError(f'No hotspot IDs found in {path}')

	return hotspots
	
def getMdVal(soup: BeautifulSoup) -> str:
	'''
	Expects
		soup: A BeautifulSoup object of the eBird login page
	Returns
		mdval: A string containing the hidden 'execution' parameter required for login
	'''
	# Find the hidden input field with name 'execution' and get its value
	exec_input = soup.select_one('input[name="execution"]')
	exec_mdval = exec_input.get('value') if exec_input is not None else None
	
	if not isinstance(exec_mdval, str) or not exec_mdval:
		raise ValueError('Could not parse eBird login execution value from login page. Check the login page structure.')

	return exec_mdval

def ebirdLogin(lgn: dict) -> requests.Session:
	'''
	Expects:
		lgn: a dict of login credentials
	Returns
		session: A session object logged ito your ebird account
	'''
	ebird_url = 'https://secure.birds.cornell.edu/cassso/login?service=https%3A%2F%2Febird.org%2Flogin%2Fcas%3Fportal%3Debird&locale=en'

	session = requests.Session()
	login_complete = False
	try:
		response = session.get(ebird_url, timeout=45) # Load logon page
		response.raise_for_status()
		execution_value = getMdVal(BeautifulSoup(response.text, 'html.parser'))
		payload = {
			'locale': 'en',
			'username': lgn['user'],
			'password': lgn['pw'], # !!!Here's your Password!!!
			'rememberMe': 'on',
			'execution': execution_value,
			'_eventId': 'submit',
			}
		response = session.post(ebird_url, data=payload, timeout=45) # !!!Here's where your password is used to log into eBird!!!
		if response.status_code == 401:
			raise requests.HTTPError(
				'eBird rejected the login (401 Unauthorized). Check your credentials and account access.',
				response=response,
			)
		response.raise_for_status()
		login_complete = True
		return session
	finally:
		if not login_complete:
			session.close()

def parseHotspots(cfg: dict, session: requests.Session, hotspots: list[str]
                  ) -> tuple[list[str], list[str]]:
	''''
	Expects:
		cfg: a dict of ebird.cfg parameters
		session: A logged in eBird session object
		hotspots: A list f hotspot IDs
	Returns:
		hs_names: A list of hotspot names, empty hotspots are omitted
		targets: A list with parsed targets data across hotspots:
				[species name, frequency, eBird species URL, hotspot name]	
	'''
	
	hotspot_names, targets = [], [] # Init lists to store hotspot names & target data
	for hotspot in hotspots: # Iterate hotspots & scrape data
		hotspot_targs, name = parseTargets(cfg, session, hotspot)
		if not hotspot_targs: # Occurs when target species data is empty
			print(f'No target species found for {name}')
			continue
		hotspot_names.append(name)
		targets.extend(hotspot_targs)
	return hotspot_names, targets

def parseListItem(target: bs4.element.Tag, hotspot_name: str) -> list[str, str, str, str]:
	'''
	Expects:
		target: a bs4 Tag containing the <li> data for a species
		hotspot_name: a str containing the hotspot name 
	Returns:
		A list [species name, frequency, eBird URL, hotspot name]
	'''
	
	header = target.find('div', {'class' : 'SpecimenHeader'}) # Species header
	if header.find('em', {'class' : 'sci'}): # find() yields bs4.element.Tag if Common + Sci displayed
		header.find('em', {'class' : 'sci'}).decompose() # Remove scientific name
	# Only psychopaths would use the Scientific name only setting, so I'm not going to deal with that
	species = header.getText().strip() # Get species common name
	species_url = 'https://ebird.org/species/'+header.find('a').get('data-species-code') # Get eBird species code
	frequency = ( target.find('div', {'class' : 'ResultsStats-stats'})
			.get('title').removesuffix('% frequency').strip() )
	return [species, frequency, species_url, hotspot_name]

def parseTargets(cfg: dict, session: requests.Session, hotspot_id: str):
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		session: A logged in eBird requests session
		hotspot_id: An eBird Hotspot ID, found in hotsot URL, (e.g. L2284561)
	Returns:
		targets: a list of lists with parsed targets data across hotspot
			data includes [species name, frequency, eBird species URL]		
	'''

	# Load hotspot target page and parse HTML
	response = session.get('https://ebird.org/targets', timeout=45, # Load hotspot target page
	                       params={'r1': hotspot_id, 'bmo': cfg['bmo'], 'emo': cfg['emo'], 
	                               'r2': cfg['reg'], 't2': cfg['list']}) 
	response.raise_for_status()
	soup = BeautifulSoup(response.text, 'html.parser') 

	# Check if login page is displayed, which indicates session may be invalid
	if soup.select_one('input[name="execution"]'):
		raise ValueError(f'Login page displayed when accessing hotspot {hotspot_id}. Session may be invalid.')
	
	# Parse hotspot name from region selection box
	hotspot_name = soup.find('option', {'value' : hotspot_id })
	if not hotspot_name:
		raise ValueError(f'Could not parse hotspot name for {hotspot_id}. Check the page structure.')
	hotspot_name = hotspot_name.getText(strip=True) # Parse hotspot name from region selection box

	targets = [] 
	for label in ('native-and-naturalized', 'exotic-provisional'):
		for section in soup.find_all('section', {'aria-labelledby': label}): #Get native or provisional
			for target in section.find_all('li'):
				targets.append(parseListItem(target, hotspot_name))
	
	print('Parsed ' + hotspot_name)
	time.sleep(4) # To limit rate of eBird page loads 

	return targets, hotspot_name

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
		.loc[:,[cfg['taxsort'], cfg['speccol']]]
		#.select([cfg['taxsort'], cfg['speccol']]) # nicer pandas >=3.1 functionality
		.drop_duplicates(subset=[cfg['speccol']])
		.dropna(subset=[cfg['speccol']])
	)
	return taxonomy
	
def processTargData(cfg: dict, targets: list, hs_names: list, taxonomy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
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

	# Get taxonomic sort as series
	tax_sort = taxonomy.set_index(cfg['speccol'])[cfg['taxsort']]

	# Create long form targets df; frequency to numeric; add taxonomic sort column
	long_targets = (
		pd.DataFrame(targets, columns=['Species', 'Frequency', 'URL', 'Hotspot'])
		.assign(Frequency=lambda df: pd.to_numeric(df['Frequency'], errors='coerce'))
		.assign(TaxSort=lambda df: df['Species'].map(tax_sort))
	)

	# Pivot to wide df  
	wide_targets= (
		long_targets.pivot(index=['Species', 'TaxSort', 'URL'], columns='Hotspot', values='Frequency')
		.fillna(value=0)
		.reset_index()
		.sort_values(by='TaxSort')
		.set_index('Species')
		.assign(MaxFreq=lambda df: df[hs_names].max(axis=1))
		.loc[lambda df: df['MaxFreq'] >= cfg['cutoff']]
		.loc[:, hs_names + ['MaxFreq', 'TaxSort', 'URL']] 
	)

	# Create URL df
	url_df = (
		wide_targets.reset_index()
		.loc[:,['Species', 'URL']]
		.set_index('Species')
	)

	wide_targets = wide_targets.drop(columns=['URL'])

	return wide_targets, url_df

def formatExcel(wb: pd.ExcelWriter.book, ws: pd.ExcelWriter.sheets, bg: str, font: str,
                last_row: int, last_col: int, min: Union(float, int), max: Union(float, int)) -> None:
	'''
	Expects:
		wb: Pandas ExcelWriter book
		ws: Pandas ExcelWriter sheet
		bg: hexadecimal cell background color
		font: hexadecimal font color
		last_row: last row to format
		last_col: last column to format
		min: minimum value to format
		max: maximum value to format
	Does:
		Applies conditional formatting to cells between min and max for cells containing
		frequency values:  2nd row / 2nd colunn to last_row / last_col,
	'''
	
	color = wb.add_format({'bg_color': bg, 'font_color': font})
	ws.conditional_format(1, 1, last_row, last_col, {'type': 'cell', 'criteria': 'between',
							'minimum': min, 'maximum' : max, 'format': color})

def writeExcel(cfg: dict, df: pd.DataFrame) -> None:
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		df: a wideform pandas data frame of ebird targets data
	Does:
		df is used to write csv and excel filesq
	'''

	outdir = Path(cfg['outdir'])
	df = df.round(decimals=1)

	df.to_csv(outdir / f"{cfg['filebase']}_targets.csv") # Write to CSV first
	
	with pd.ExcelWriter(outdir / f"{cfg['filebase']}_targets.xlsx", engine='xlsxwriter') as writer:
		name = cfg['filebase']+' Targets' # Sheet name
		df.to_excel(writer, sheet_name=name) # Write data
	
		# Get workbook, worksheet, and dimensions for formatting
		book = writer.book
		sheet = writer.sheets[name]
		last_col, last_row = sheet.dim_colmax-1, sheet.dim_rowmax
		cut = cfg['cutoff']

		# Format frequency colors
		formatExcel(book, sheet, '#D0D0D0', '#D0D0D0', last_row, last_col, 0, cut)
		formatExcel(book, sheet, '#FFC7CE', '#9C0006', last_row, last_col, cut, 10)
		formatExcel(book, sheet, '#FCEAA6', '#935A1D', last_row, last_col, 10, 25)
		formatExcel(book, sheet, '#ACC8E9', '#1F3D61', last_row, last_col, 25, 50)
		formatExcel(book, sheet, '#C6EFCE', '#006100', last_row, last_col, 50, 100)

		# General formatting
		data_format = book.add_format({'border': 1, 'bold': True, 'font_size': 14 })
		sheet.set_column(1, last_col+1, 15, cell_format=data_format)

		# Define hotspot & species formats
		hs_format = book.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
									'align': 'center', 'border': 1, 'font_size': 15 })
		sp_format = book.add_format({'bold': True, 'align': 'right', 'border': 1, 'font_size': 15 })

		# Write formats by rewriting original data into cells with formatting
		# Really annoying method, but is recommended in xlsxwriter docs
		# There may be better way, but this maintains compatibility with multiple pd versions
		for i, value in enumerate(df.columns):
			sheet.write(0, i + 1, value, hs_format)
		for i, (idx, row) in enumerate(df.iterrows()):
			sheet.write(i+1, 0 , idx, sp_format)
	
		# Size first row & first column
		sheet.set_column('A:A', 40)
		sheet.set_row(0, 80)

def getAuthenticatedSession(target_url: str) -> requests.Session:

	from playwright.sync_api import sync_playwright
	
	session = requests.Session()
	user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

	p = sync_playwright().start()
	browser = p.chromium.launch(headless=True)
	context = browser.new_context(user_agent=user_agent)
	page = context.new_page()

    # Navigate to the protected page
	page.goto(target_url, wait_until="domcontentloaded")

    # Wait until the Anubis auth cookie is set after the PoW finishes
	auth_cookie = None
	for _ in range(30):  # Poll for up to 15 seconds
		cookies = context.cookies()
		for cookie in cookies:
			if "anubis-auth" in cookie["name"]:
				auth_cookie = cookie
				break
		if auth_cookie:
			break
		page.wait_for_timeout(500)

	if not auth_cookie:
		browser.close()
		raise RuntimeError("Timed out waiting for Anubis challenge to complete.")

    # Transfer all cookies and matching headers to requests.Session
	for cookie in context.cookies():
		session.cookies.set(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie["domain"],
            path=cookie["path"],
        )
	
	session.headers.update({"User-Agent": user_agent})
	return session, browser, p

def parseSpeciesPage(soup: BeautifulSoup) -> tuple[str, str]:
	'''
	Expects:
		soup: A BeautifulSoup object
	Returns:
		img_url: A string containing the image URL for the species
		description: A string containing the species description text
	'''

	# Remove last 3 digits from URL (default 320),replace with 640 for higher res image
	img_url = soup.find('img', {'class' : 'Species-media-image'}).get('src')[:-3] + '640'
	description = (
		soup.find('div', {'class' : 'Species-identification-text'})
		.find_next('p', {'class' : 'u-stack-sm'})
		.getText(strip=True)
	)
	return img_url, description

def getSpeciesPages(df: pd.DataFrame, outdir: Path) -> list[tuple[str, pd.Series, str, str]]:
	'''
	Expects:
		df: a pandas dataframe of species URLs
		outdir: the directory where downloaded species images will be stored
	Returns:
		species_data: a list of tuples containing species data 
			(species name, pandas species row, image path, description)
	'''

	# Get authenticated playwright session
	session, browser, p = getAuthenticatedSession(df.iloc[0]['URL'])

	# Output directory for media
	media_dir = outdir / 'media'
	media_dir.mkdir(parents=True, exist_ok=True)

	try:
		species_data = []
		for species, species_row in df.iterrows():
			# Open species page
			response = session.get(species_row['URL'], timeout=45)
			response.raise_for_status()
			soup = BeautifulSoup(response.text, 'html.parser')

			# Parse page to get image url and species description
			img_url, description = parseSpeciesPage(soup)

			# Open image page
			image_response = session.get(img_url, timeout=45)
			image_response.raise_for_status()

			# Create file name and write to file
			safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', str(species)).strip('_')
			image_filename = f'{safe_name}.jpg'
			(media_dir / image_filename).write_bytes(image_response.content)
			species_data.append((species, species_row, f'media/{image_filename}', description))
			print(f'{species} page parsed')
			time.sleep(1)  # To limit rate of eBird page loads

	finally:
		browser.close()
		p.stop()

	return species_data

def getStudyGuideStart() -> str:
	'''
		Expects: No arguments
		Returns:
			html_style: str containing first part of HTML page
	'''

	html_style = '''<!DOCTYPE html>
		<html lang="en">
		<head>
			<meta charset="utf-8">
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<title>eBird Study Guide</title>
			<style>
				:root {
					color-scheme: light;
					font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
					color: #23332b;
					background: #F3FAFD;
				}
				* { box-sizing: border-box; }
				body { margin: 0; }
				main { width: min(100% - 2rem, 52rem); margin: 3rem auto; }
				header { margin-bottom: 1.5rem; }
				h1 { margin: 0 0 .5rem; font-size: clamp(2rem, 5vw, 3rem); }
				.brand { font-family: Avenir, sans-serif; }
				.brand-e { color: #4B8050; }
				.brand-bird { color: #2D2620; }
				header p { margin: 0; color: #53645a; line-height: 1.6; }
				ul { display: grid; gap: .65rem; margin: 0; padding: 0; list-style: none; }
				li {
					overflow: hidden;
					border: 1px solid #dce5dd;
					border-radius: .75rem;
					background: #fff;
					box-shadow: 0 2px 6px rgb(35 51 43 / 5%);
					transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
				}
				a { display: block; padding: .9rem 1rem; color: #405A73; font-weight: 600; text-decoration: none; }
				.species-link { padding-bottom: .3rem; }
				.bow-link { padding-top: 0; font-size: .875rem; }
				.species-media { display: block; width: 100%; height: auto; border: 0; background: #e9eef2; }
				.species-description { margin: 0; padding: 1rem; color: #53645a; line-height: 1.6; }
				li:hover { transform: translateY(-1px); border-color: #9ab9a5; box-shadow: 0 5px 14px rgb(35 51 43 / 10%); }
				a:focus-visible { outline: 3px solid #e6a23c; outline-offset: -3px; }
				@media (prefers-reduced-motion: reduce) {
					li { transition: none; }
				}
			</style>
		</head>
		<body>
			<main>
				<header>
					<h1><span class="brand"><span class="brand-e">e</span><span class="brand-bird">Bird</span></span> Study Guide</h1>
					<p>Species are listed in taxonomic order. Select a name to view its eBird account.</p>
				</header>
				<ul>
		'''

	return html_style

def writeURLs(cfg: dict, df: pd.DataFrame) -> None:
	'''
	Expects:
		cfg: a dict of ebird.cfg parameters
		df: a pandas dataframe of species URLs
	Does:
		Writes a linked HTML study guide
	'''

	outdir = Path(cfg['outdir'])

	with (outdir / f"{cfg['filebase']}_study_guide.html").open('w', encoding='utf-8') as f:
		# Write webpage style, headers, etc
		f.write(getStudyGuideStart())
		
		species_data = None
		#species_data = getSpeciesPages(df, outdir)
		
		if species_data:
			iter_species = species_data 
			outdir = Path(cfg['outdir']+'/media')
		else:
			iter_species = df.iterrows()

		for data in iter_species:
			name = html.escape(str(data[0]), quote=True)
			url = html.escape(str(data[1]['URL']), quote=True)
			bow = url.replace('ebird.org','birdsoftheworld.org/bow')+'/cur/introduction'
			f.write(
				f'\t\t\t<li><a class="species-link" href="{url}" '
				f'target="_blank" rel="noopener noreferrer">{name}</a>'
			)
			f.write(
				f'\t\t\t<a class="bow-link" href="{bow}" '
				f'target="_blank" rel="noopener noreferrer">Birds of The World</a>'
			)
			if species_data:
				img_loc = html.escape(str(data[2]), quote=True)
				description = html.escape(str(data[3]), quote=True)
				f.write(
					f'<img class="species-media" src="{img_loc}" '
					f'alt="{name}" loading="lazy">'
					f'<p class="species-description">{description}</p>'
				)
			f.write('</li>\n')
		f.write('''		</ul></main></body></html>''')
		
def main() -> None:
	
	# !!! Read config file, your password is read here, see getConfig() code!!!
	cfg, lgn = getConfig('ebird.cfg') 
	
	Path(cfg['outdir']).mkdir(exist_ok=True)
	hotspots = getHotspots(cfg['hotspots']) # Read hotspots file
	taxonomy = readTaxonomy(cfg) # Read taxonomy csv used by eBird

	region = cfg['reg']
	list_type = cfg['list']
	start_month = calendar.month_name[int(cfg['bmo'])]
	end_month = calendar.month_name[int(cfg['emo'])]
	print(
		f'Parsing targets for your {region} {list_type} list from {start_month} '
		'to {end_month} across {len(hotspots)} hotspots/regions.\n\n'
	)
	
	# Login to eBird and parse hotspot target pages
	
	# !!! Your password is used to login to eBird here. See ebirdLogin!!!
	session = ebirdLogin(lgn) 
	try:
		# !!!Delete your password from lgn so you don't have to look through code for rest of subfunctions!!!
		del lgn['pw'] 
		del lgn['user']
		hs_names, targets = parseHotspots(cfg, session, hotspots) # Visits hotspot targets pages and parses data
	finally:
		session.close()

	# Process parsed data into pandas dataframes
	targ_df, url_df = processTargData(cfg, targets, hs_names, taxonomy) # Use pandas to wrangle data into tables for output

	if not targ_df.empty:
		print(f'\n\nFound {targ_df.shape[0]} targets in {targ_df.shape[1]-2} hotspots/regions\n')
		writeExcel(cfg, targ_df)
		writeURLs(cfg, url_df)
	else:
		print('No target species found above cutoff frequency. No output files created.')
        		
if __name__ == '__main__':
	main()