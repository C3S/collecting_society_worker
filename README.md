 c3sFingerprinting README
==========================

This is the numbercruncher we will use for generating fingerprints for whole 
audio files that artists have uploaded and to match monitored use of music so it 
can be associated with artists. It uses click to run as a command line tool
with the options like `preview`, `checksum`, or `fingerprint`.

This is the current implementation status:

* preview
    1. creates a smaller audio preview file
    2. cuts out a one minute excerpt from the file
    3. retrieves metadata from the file and provides it in the content db table
* checksum:
    1. looks for files in `previewed_path` (see config.ini)
    2. hashes it with sha256, both, the complete file and each 1MiB block of the file
    3. moves it into `checksummed_path`
    4. sets the status in the `creation` table
    5. writes the hash to the `content` table
* fingerprint
    1. looks for files in `checksummed_path` (see config.ini) and uses *echoprint-codegen* to get a raw json with an audiofingerprint
    3. fills in metadata that is missing in the json from the `content` and `creation` tables via *proteus*
    4. sets the status in the `creation` table to *fingerprinted*
    5. uploads ('ingests') the jsons including the fingerprints to our EchoPrint server
    6. makes a test query before and after ingesting the print and stores statistical data (score, uniqueness factor)
    7. moves the file into `fingerprinted_path`

Command Line Options
--------------------
* `./repro.py preview` - previews an audiofile
* `./repro.py checksum` - hashes an audiofile
* `./repro.py fingerprint` - fingerprints an audiofile
* `./repro.py all` - does all the above steps with a priority on preview
* `./repro.py loop` - repeats `all` option endlessly with 10 sec pauses in between

* ./repro.py all

Getting Started
---------------

* sudo apt-get install libpq-dev
* git clone git@github.com:C3S/c3sRepertoireProcessing.git 
* cd c3sRepertoireProcessing
* cp development.ini.EXAMPLE development.ini 
* cp production.ini.EXAMPLE production.ini
* cp config.ini.EXAMPLE config.ini
* pip install virtualenv # setup own python environment
* virtualenv env
* env/bin/python setup.py develop # only once
* build an EchoPrint fingerprinter binary in ../echoprint-codegen/echoprint-codegen
* get ffmpeg (recommended: download static build to /usr/bin)
* setup & run c3s.ado.repertoire and get some 'uploaded' sample data from 
  ado/etc/tmp/upload after uploading some audio files
* chown a+x repro.py
* ./repro.py all