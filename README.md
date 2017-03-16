 c3sFingerprinting README
==========================

This is the numbercruncher we will use for generating fingerprints for whole 
audio files that artists have uploaded and to match monitored use of music so it 
can be associated with artists. It uses click to run as a command line tool
with the commands `get-jobs` and `match`:

The project is in an early stage. This is the current implementation status:

* get-jobs
    * implemented:
        1. looks for files in `complete_path` (see config.ini)
        2. uses *echoprint-codegen* to get a raw json with an audiofingerprint
        3. fills in metadata that is missing in the json from the `content` 
        and `creation` tables via *proteus*
        4. sets the status in the `creation` tables to *fingerprinted*
        5. uploads ('ingests') the jsons including the fingerprints to our 
        EchoPrint server
    * not yet implemented:
        1. moves the processed files from the `complete_path` to the 
        `for_archiving_path` folder
        2. tracks if files have been moved to all necessary offline archives 
        and deletes those files
        3. sets the status in the `creation` tables to *archived*

* match
    --> todo

Getting Started
---------------

* sudo apt-get install libpq-dev
* git clone git@github.com:C3S/c3sFingerprinting.git 
* cd c3sFingerprinting
* cp development.ini.EXAMPLE development.ini 
* cp production.ini.EXAMPLE production.ini
* cp config.ini.EXAMPLE config.ini
* pip install virtualenv # setup own python environment
* virtualenv env
* env/bin/python setup.py develop # only once
* build an EchoPrint fingerprinter binary in ../echoprint-codegen/echoprint-codegen
* get ffmpeg (recommended: download static build to /usr/bin)
* setup & run c3s.ado.repertoire and get some 'complete' sample data from 
  ado/etc/tmp after uploading some audio files
* chown a+x fingerprint
* ./fingerprint get-jobs