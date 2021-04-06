# Cryptocurrencies
### Table of contents
* [Setup](#setup)
* [Settings](#settings)
* [Available commands](#available-commands)
* [Technologies](#technologies)

### Setup
Download the repository and prepare a new virtual environment. Then install all dependencies using the command:
```
$ pip install -r requirements.txt
```
From this point, you can proceed to use the commands described [below](#available-commands).
The attached database file (db/crypto.db) already has tables created but does not contain any data.

However, If you'd like to create your own database file, just delete the crypto.db file or rename the database file in the settings (check [Settings](#Database-filename)).
Then run the following script:
```
python models.py
```
It will create a new database file and migrate all models.

This concludes the project setup. [Here](#available-commands) you can find information how to use available commands.


### Settings

The settings.py file contain the configuration for the following:
* database name and path to it
* information required to download data form the Coinpaprika API (endpoints, etc)
* configuration of data modifications to be performed on downloaded data (to make them compatible with the database model)

##### Database filename
To rename the database file, change the value of the DB_FILENAME variable, by default set to 'crypto.db':
```
DATABASE = 'crypto.db'
```
Remember to run models.py script to create a new database file and migrate models.

##### Other settings
The other settings are responsible for how the program interacts wit the API and process data received from it.
It is NOT recommended to make changes to them as it may cause program malfunctions.

### Available commands

All commands are called from the historical.py script.  

General usage:  historical.py [OPTIONS] COMMAND [ARGS]

where:  
OPTIONS are arguments used by every command described below  
COMMAND is the name of the command  
ARGS - are command-specific arguments (described under each command if any).


OPTIONS:  
--start-date - choose start date, format YYYY-MM-DD or YYYY-MM  
--end-date - choose end date,  format YYYY-MM-DD or YYYY-MM  
--coin - specify the name of the cryptocurrency, default is "btc-bitcoin"  
--ohlc [open|close|high|low] - choose one of the OHLC values, default is "close"  

'--start-date' and '--end-date' arguments are mandatory, you will be prompt about them if you don't pass them to command.
There are two formats allowed (YYYY-MM-DD or YYYY-MM), but remember that short one will be understood as an entire month, ie:  
this:
```
--start-date=2020-01 --end-date=2020-03
```
is equivalent of:
```
--start-date=2020-01-01 --end-date=2020-03-31
```

**1. _consecutive-increasee_ - display the longest consecutive period in which the currency price was rising**
  
 Command pattern: historical.py [OPTIONS] consecutive-increasee 
  
 Example inputs:
 ```
 python historical.py --start-date=2020-01-01 --end-date=2020-03-31 consecutive-increasee
 python historical.py --start-date=2020-01-01 --end-date=2020-03-31 --coin=usdt-tether consecutive-increasee
 ```

**2. _average-price-by-month_ - display the monthly average price of the currency over the given period**

 Command pattern: historical.py [OPTIONS] average-price-by-month 
 
 Example inputs:
 ```
 python historical.py --start-date=2020-01 --end-date=2020-03 average-price-by-month
 python historical.py --start-date=2020-01 --end-date=2020-03 --coin=usdt-tether average-price-by-month
 ```
It is advisable to pass the dates in a short format (YYYY-MM). Note that using the YYYY-MM-DD date format will cause the 
calculation to be performed from and to a specific day, not necessarily for the entire month.  


**3. _export_ - export data for given period to a file**

Command pattern: historical.py [OPTIONS] export [ARGS]

Args:  
--format ['csv', 'json'] - choose file format, default is "csv"  
--file - choose the name of the file, default is "historical_data" 

 Example input:  
 ```
 python historical.py --start-date=2020-01 --end-date=2020-03 export
 python historical.py --start-date=2020-01 --end-date=2020-03 export --format=json --file=data
 ```
  
### Technologies
* Python 3.8.8
* peewee 3.13.4
* click 7.1.2
* SQLite 3.22.0
* pytest 6.2.3