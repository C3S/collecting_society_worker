 c3sFingerprinting README
==========================

This is the numbercruncher we will use for generating fingerprints for whole 
audio files that artists have uploaded and to match monitored use of music so it 
can be associated with artists. It uses click to run as a command line tool
with the commands `checksum` and `fingerprint`:

The project is in an early stage. This is the current implementation status:

* checksum
    * implemented:
        1. looks for files in `previewed_path` (see config.ini)
        2. hashes it with sha256
        3. moves it into `checksummed_path`
        4. sets the status in the `creation` table
    * not yet implemented:
        1. writing of the hash to the `content` table
* fingerprint
        2. looks for files in `checksummed_path` (see config.ini) and uses 
           *echoprint-codegen* to get a raw json with an audiofingerprint
        3. fills in metadata that is missing in the json from the `content` 
        and `creation` tables via *proteus*
        4. sets the status in the `creation` table to *fingerprinted*
        5. uploads ('ingests') the jsons including the fingerprints to our 
        EchoPrint server
        6. moves the file into `fingerprinted_path`
    * not yet implemented:
        1. Previewing
        2. Updating of metadata

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
* setup & run c3s.ado.repertoire and get some 'uploaded' sample data from 
  ado/etc/tmp/upload after uploading some audio files
* chown a+x repro.py
* ./repro.py fingerprint