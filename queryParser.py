import re


USE_DEFINITNION=True

def empty_column(**kwargs):
	col = dict(
		name=None, 
		definition=None, 
		label= None, 
		kind=None
		)

	for k, val in kwargs.items():
		col[k]=val

	return col

def empty_table(**kwargs):
	table = dict(
		table=None, 
		schema=None, 
		alias=None, 
		join_condition=None, 
		joined_alias = [], 
		kind=None, 
		nested_object=None
		)

	for k, val in kwargs.items():
		table[k]=val
		
	return table 

def empty_query(**kwargs):
	query_obj = dict(
		is_distinct=False,
		columns = [], # dict(name='', definition='', label='', kind=''),
		tables = [], # dict(table='', alias='', join_condition='', join_column=''),
		filters =None,
		union = [],
		ctes=dict(),
		group_by=None, 
		order_by=None,
		limit=None,
		offset=None,
		having=None
		)
	for k, val in kwargs.items():
		query_obj[k]=val
		
	return query_obj

def is_alpha(c):
	return c.replace('_','').isalpha()


def remove_comments(string):
	string = re.sub(re.compile("--.*?\n", re.DOTALL ) ,"" ,string) # remove all occurance streamed comments (/*COMMENT */) from string
	return string


def replace_words(string, options, before_string, after_string, upper=False):
	"""
	replaces all the words with the same word but with string
	"""
	new_string = string
	for o in options:
		pattern = re.compile(o, re.IGNORECASE)
		new_string = pattern.sub('{b}{word}{a}'.format(b=before_string, word=o.upper() if upper else o,  a=after_string), new_string)
	return new_string

def title(c):
	return c.replace('_',' ').title()

def get_between_to_end_of_str(text, from_letter):
	if text is None:
		return ''

	parts = []
	start_saving = False
	for s in text:
		# if you don't have a string then save it 
		if start_saving and not is_alpha(s) and s !='_' :
			return ''.join(parts)
		# add the letters
		if s == from_letter:
			start_saving = True
		elif start_saving:
			parts.append(s) 
	return ''.join (parts)

def replace_space_in_quotes(text):
	new_text = []
	in_quotes=False
	for t in text:
		if t == "'":
			in_quotes = not in_quotes

		if in_quotes and t == ' ':
			new_text.append('--')
		elif not in_quotes and t in ('(', ')', ','):
			new_text.append(' {} '.format(t))
		else:
			new_text.append(t)

	return ''.join(new_text)


def find_comma(components):
	parenthsis=0
	for ii, s in enumerate(components):
		# find the end of the columns
		parenthsis += s.count('(')
		parenthsis -= s.count(')')
		if parenthsis ==0 and s ==',' or s.endswith(',') or s.lower() == 'from':
			new_idx = ii+1
			break

	return ii+1

def track_parenthes(text, is_in_quotes):
	p = 0

	for s in text:
		if s=="'":
			is_in_quotes = not is_in_quotes

		elif not is_in_quotes:
			if s == '(':
				p +=1
			elif s == ')':
				p -=1

	return (p, is_in_quotes)



def parse_column(components):
	"""
	Gets the column for the object
	"""
	column_obj = empty_column()

	parenthsis=0
	definition = []
	is_in_quotes=False

	# get the definition and name
	for ii, s in enumerate(components):
		print('cp - ' + s)
		print(parenthsis)
		print(is_in_quotes)

		(p, is_in_quotes) = track_parenthes(s, is_in_quotes)
		# append the parenthies

		# if it is the next column then skip one 
		if  parenthsis == 0 and not is_in_quotes:
			if s.lower() in (',','from', ):
				column_obj['name'] = ' '.join(definition)
				column_obj['definition'] = ''
				new_idx = ii + 1
				break

			elif components[ii+1].lower() in (',','from', ):
				column_obj['name'] = s.replace('"','')
				column_obj['definition'] = ' '.join(definition).replace('--',' ')
				new_idx = ii+2
				break

		if s.lower() != 'as':
			definition.append(s)

		parenthsis += p

	# figure out it null
	if column_obj['definition'] is not None and get_between_to_end_of_str(column_obj['definition'].lower(),'n') == 'ull':
		column_obj['definition'] = None

	# return the label
	if USE_DEFINITNION:
		column_obj['label'] = title(get_between_to_end_of_str(column_obj['definition'] , '.'))

	if not USE_DEFINITNION or column_obj['label'] == '':
		column_obj['label'] = title(column_obj['name'].split('.')[-1])

	# use the name to figure out the kind
	column_obj['kind'] = get_type(column_obj['name'])
	return (new_idx, column_obj)

def parse_ctes(components):
	"""
	parse ctes
	"""
	print('parsing ctes + %s' % ' '.join(components[:10]) )
	idx=0
	len_c = len(components)
	ctes = dict()
	name = None
	parenthsis = 0
	is_in_quotes = False

	while idx < len_c and components[idx].lower() != 'select':
		(p, is_in_quotes) = track_parenthes(components[idx], is_in_quotes)
		parenthsis +=p

		# get hte name
		if is_alpha(components[idx]) and components[idx].lower() not in ('as', 'with', ):
			name = components[idx]
		
		# start the components
		if parenthsis > 0:
			(ii, obj) = parse_components(components[idx+1:], ctes)
			ctes[name] = obj
			idx += ii 

		idx +=1
	return (idx, ctes)

def parse_table(components, ctes):
	"""
	Gets the column for the object
	"""
	#print(components)

	len_c = len(components)
	table_obj = empty_table()
	table_obj['kind'] = []
	table_obj['join_condition'] = []

	idx = 0
	looking_for = 'join'  # table, alias, 
	joins = ('left', 'right', 'full', 'inner', 'cross', 'join','from', )

	while idx < len_c:

		c = components[idx].lower() #.replace('(','').replace(')','')
		if c in ('where', 'union', 'all', 'group', 'order', 'limit', ):
				# print('breaking from c')
				idx -= 1
				break

		if looking_for =='join':
			if components[idx] in (')',):
				break
			if c in joins:
				table_obj['kind'].append(c)
			
			if c in ('join', 'from', ',', ):
				#print('found from or join')
				looking_for = 'table'
				if c == ',':
					table_obj['kind'].append('cross join')

		elif looking_for == 'table':
			if components[idx] =='(':
				(new_idx, query_obj) = parse_components(components[idx+1:], ctes)
				idx = idx + new_idx + 1
				table_obj['nested_object']= query_obj
				looking_for = 'alias'
			
			elif '.' in c:
					(table_obj['schema'] ,table_obj['table'])= c.split('.')
					#print('found table and schema ')
					looking_for = 'alias'
			elif is_alpha(c) and c in ctes.keys():
					table_obj['table'] = c
					table_obj['nested_object'] = ctes[c]
					#print('found cte')
					looking_for = 'alias'


		elif looking_for == 'alias':
			if c in ('join',):
				looking_for = 'join'
				idx -=1

			elif c == 'on':
				looking_for = 'join_condition'
				parenthsis = 0
			elif c in ('where',')',):
				idx -= 1
				break
			elif c not in ('as',) and is_alpha(c):
				table_obj['alias'] = c
				looking_for = 'on'
				if table_obj['kind'][-1] != 'join':
					break
		
		elif looking_for == 'on':
			if c == 'on':
				looking_for= 'join_condition'
				parenthsis = 0
				is_in_quotes = False


		elif looking_for == 'join_condition':

			(p,is_in_quotes) = track_parenthes(components[idx], is_in_quotes)
			parenthsis += p

			table_obj['join_condition'].append(components[idx])
			if '{}.'.format(table_obj['alias']) not in c and '.' in c:
				table_obj['joined_alias'].append(c.split('.')[0])

			if parenthsis == 0:
				break

		idx +=1

	table_obj['kind'] = ' '.join(table_obj['kind'])
	table_obj['join_condition'] = ' '.join(table_obj['join_condition']) if len(table_obj['join_condition'])>0 else None
	table_obj['joined_alias'] =list(set(table_obj['joined_alias']))

	return (idx + 1, table_obj)

def parse_filter(components, kind):
	"""
	Parese any filter 
	"""
	filters = [] 
	pieces = kind.split('_')
	parenthsis =0
	is_in_quotes = False
	start_tracking = False
	# loop the the data 
	for ii, s in enumerate(components):
		#print('where - ' + s)

		# find the end of the columns
		(p, is_in_quotes) = track_parenthes(s, is_in_quotes)
		parenthsis += p

		if parenthsis <0 or (s.lower() not in pieces and s.lower() in ('union', 'group', 'order', 'limit', )):
			ii -= 1
			break
		elif parenthsis==0 and s.lower() in pieces:
			pieces.remove(s.lower())
			if len(pieces) == 0:
				start_tracking = True
		elif start_tracking:
			filters.append(s)

	if len(filters) > 0:
		return (ii + 1 , ' '.join(filters))
	else:
		return (0, None)


def parse_components(query_components, ctes = None):
	"""
	Parses  a query for the details of the query
	"""
	#print(query_components)

	print('---- STARTING ----')
	print(query_components)

	query_obj = empty_query()

	# handle nested ctes
	if ctes is not None:
		query_obj['ctes'] = ctes

	idx = 0
	len_c = len(query_components)

	while idx < len_c and query_components[idx-1].lower() not in ('from',):
		if query_components[idx].lower() in ('select',):
			idx +=1
			if query_components[idx].lower() in ('distinct',):
				idx +=1
				query_obj['is_distinct']=True

		elif query_components[idx].lower() in ('with',):
			(new_idx, ctes) = parse_ctes(query_components[idx+1:])
			query_obj['ctes'] = {**query_obj['ctes'], **ctes}
			idx += new_idx + 2

		# parse the column 
		(new_idx, col) =parse_column(query_components[idx:])
		idx += new_idx
		#print('adding columns ' + str(col))
		query_obj['columns'].append(col)


	idx -= 1
	while idx < len_c and  query_components[idx].lower() not in ('where', 'union', ')',) :
		(new_idx, table) = parse_table(query_components[idx:], query_obj['ctes'])
		if table['nested_object'] is not None:
			query_obj['ctes']={**query_obj['ctes'], **table['nested_object']['ctes']}
		idx += new_idx
		if table['kind'] == '':
			break
		query_obj['tables'].append(table)

	
	# Add the where statements
	if idx < len_c:
		(new_idx, filters) = parse_filter (query_components[idx:], 'where')
		idx += new_idx
		query_obj['filters'] = filters

	# PARSE GROUP BY
	if idx < len_c:
		(new_idx, group_by) = parse_filter(query_components[idx:], 'group_by')
		idx += new_idx
		query_obj['group_by'] =  group_by.split(',')  if group_by is not None else None

	# PARSE ORDER BY
	if idx < len_c:
		(new_idx, order_by) = parse_filter (query_components[idx:], 'order_by')
		idx += new_idx
		query_obj['order_by'] = order_by.split(',') if order_by is not None else None

	# Parse HAVING
	if idx < len_c and query_obj['group_by'] is not None:
		(new_idx, having) = parse_filter(query_components[idx:], 'having')
		idx += new_idx
		#print('adding filters ' + str(filters))
		query_obj['having'] = having

	
	# parse the UNION ALL
	if idx < len_c and query_components[idx].lower() in ('union',):
		kind = 'union'
		# check if it all
		if query_components[idx+1].lower() in ('all',):
			kind = 'union all'
			idx+=1

		# find the select
		while idx<len_c:
			if query_components[idx].lower() == 'select':
				break
			idx +=1

		# parse the objects
		(new_idx, obj) = parse_components(query_components[idx:], query_obj['ctes'])
		query_obj['ctes'] = {**obj['ctes'], **query_obj['ctes']}

		idx += new_idx
		#print('adding table ' + str(table))
		query_obj['union'].append(dict(kind=kind, nested_object = obj))



	# PARSE ORDER BY
	if idx < len_c:
		(new_idx, limit) = parse_filter(query_components[idx:], 'limit')
		idx += new_idx
		query_obj['limit'] = int(limit) if limit is not None else None

	# print(query_obj)
	return (idx, query_obj)


def obj_to_query(obj, tab=0, use_cte=True):
	query =  []

	# hanlde the CTES
	if use_cte and len(obj['ctes'].keys())>0:
		query.append('WITH')
		for k, item in obj['ctes'].items():
			query.append('{} AS ('.format(k))
			query.append(obj_to_query(item, tab+1, use_cte =False))
			query.append('{tab}),'.format(tab='\t'*(tab)))

		# removes the comma
		query[-1]=')'

	# add the select
	query.append('{tab}SELECT'.format(tab='\t'*(tab)))

	if obj['is_distinct']:
		query.append('{tab}DISTINCT'.format(tab='\t'*(tab+1)))
	
	# convert the columns
	for ii, c in enumerate(obj['columns']):
		query.append('{tab} {comma}{definition} {name}'.format(
			tab='\t'*(tab+1),
			name= c['name'],
			definition = convert_definition(c['definition'], get_type(c['name']), '\t'*(tab+1)),
			comma = ', ' if ii>0 else ''
			)
		)

	# add the main code
	for ii, t in enumerate(obj['tables']):
		if t['table'] is not None:
			query.append(
				'{tab}{kind} {schema}{table} {alias}'.format(
					tab = '\t'*tab,
					kind=t['kind'].upper(), 
					schema = t['schema'] + '.' if t['schema'] is not None else '',
					table = t['table'],
					alias = 'AS {}'.format(t['alias']) if t['alias'] is not None else ''
					)
			)
		# handle nested objectes
		elif t['nested_object'] is not None:
			query.append('{tab}{kind} ('.format(tab='\t'*tab, kind=t['kind'].upper()))
			query.append(obj_to_query(t['nested_object'], tab+1, use_cte =False))
			query.append('{tab}) AS {alias}'.format(alias=t['alias'], tab= '\t'*tab) if t['alias'] is not None else '{tab})'.format(tab= '\t'*tab))


		if t['join_condition'] is not None:
				query.append('{tab}ON {condition}'.format(
					tab='\t'*(tab+1),
					condition = t['join_condition']
					))

	# add the filters
	if obj['filters'] is not None:
		query.append('{tab}WHERE {filter}'.format(
				tab='\t'*tab, 
				filter=replace_words(obj['filters'], ['and ', 'or '], '\n'+'\t'*(tab+1), '', upper=True)
				))

	# group by 
	if obj['group_by'] is not None:
		query.append('{tab}GROUP BY {group_by}'.format(tab='\t'*tab, group_by= ', '.join(obj['group_by'])))

	# order by 
	if obj['order_by'] is not None:
		query.append('{tab}ORDER BY {order_by}'.format(tab='\t'*tab, order_by= ', '.join(obj['order_by'])))

	# add the filters
	if obj['having'] is not None:
		query.append('{tab}HAVING {having}'.format(
				tab='\t'*tab, 
				having=replace_words(obj['having'], ['and ', 'or '], '\n'+'\t'*(tab+1), '', upper=True)
				))

	# add the unions
	for u in obj['union']:
		query.append('\n'+u['kind'].upper() +'\n')
		query.append(obj_to_query(u['nested_object'], tab, use_cte =False))

	# add the filters
	if 'limit' in obj.keys() and obj['limit'] is not None:
		if isinstance(obj['limit'], list):
			obj['limit']= obj['limit'][0]

		query.append('{tab}LIMIT {limit}'.format(tab='\t'*tab, limit = str(obj['limit'])))


	# add the filters
	if 'offset' in obj.keys() and obj['offset'] is not None:
		query.append('{tab}OFFSET {offset}'.format(tab='\t'*tab, offset = str(obj['offset'])))
		
	return '\n'.join(query)


def convert_definition(d, kind, tab):

	if d == '':
		col = ''
	elif d is None:
		col = 'NULL'
		if kind in ('revenue', 'number',):
			col += ' ::FLOAT'
		elif kind == 'timestamp':
			col += ' ::TIMESTAMP'
		elif kind == 'string':
			col += ' ::VARCHAR(255)'
	else:
		d = replace_words(d, ['case '], '', '', upper=True)
		d = replace_words(d, [' end'], '\n' +tab, '', upper=True)
		d = replace_words(d, ['when ', 'else '], '\n' +tab + '\t', '', upper=True)

		col = '{} AS '.format(d)
	return col


def parse_query(query):

	# remove the comments
	query = remove_comments(query)
	# replace all query spaces with --then we will replace it at the end
	query_components = [q.replace('--',' ') for q in replace_space_in_quotes(query).split()]

	obj = parse_components(query_components)

	return obj


def get_tables_for_autocorrect(query):
	"""
	Gets all the tables and nested queries
	"""
	(_, query_obj) = parse_query(query)

	auto_obj = [] #dict(schema='', table='', alias = '', override_columns = None)

	for t in query_obj['tables']:
		if t['schema'] is not None:
			auto_obj.append(dict(
				schema = t['schema'],
				table = t['table'],
				alias = t['alias'],
				override_columns = []
			))
		elif t['nested_object'] is not None:
			auto_obj.append(dict(
				schema = None,
				table = None,
				alias = t['alias'],
				override_columns = [c['name'] for c in t['nested_object']['columns']]
			))

	return (auto_obj, query_obj)



def format_query(query):
	"""
	format the query 
	"""
	(_, query_obj) = parse_query(query)
	query = obj_to_query(query_obj)
	return query
