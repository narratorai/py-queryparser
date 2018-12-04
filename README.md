# py-queryparser
A python query parser for Redshift 


### Getting Started

1. Clone this repo:

```
git clone git@github.com:narratorai/py-queryparser.git
```


### Ussage

#### Parse a query 

```
import queryParser

(_ , query_object) = queryParser.parse_query(query)
```


#### Convert query object to query 

```
import queryParser

query = queryParser.obj_to_query(query)
print(query)
```


#### Formatting a query
This just parses the query then generates the query from the output object

```
import queryParser

queryParser.format_query(query)
```

