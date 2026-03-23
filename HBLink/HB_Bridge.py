#!/usr/bin/env python3
#
###############################################################################
#   Copyright (C) 2017 Mike Zingman N4IRR
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
###############################################################################

'''
HB_Bridge Python 3 Modernized Version
'''

# Python modules we need
import sys
import socket
import configparser
import _thread as thread
import traceback
from bitarray import bitarray
from bitstring import BitArray, BitStream
import struct
from time import time, sleep, localtime, strftime
from importlib import import_module
from binascii import b2a_hex as ahex
from random import randint
from threading import Lock

# Twisted is pretty important, so I keep it separate
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet import task

# Things we import from the main hblink module
from hblink import HBSYSTEM, systems, int_id, hblink_handler
from dmr_utils.utils import hex_str_3, hex_str_4, int_id, get_alias
from dmr_utils import decode, bptc, const, golay, qr
import hb_config
import hb_log
import hb_const
from dmr_utils import ambe_utils
from dmr_utils.ambe_bridge import AMBE_HB

# Metadata
__author__     = 'Mike Zingman, N4IRR and Cortney T. Buffington, N0MJS'
__copyright__  = 'Copyright (c) 2017 Mike Zingman N4IRR'
__credits__    = 'Cortney T. Buffington, N0MJS; Colin Durbridge, G4EML, Steve Zingman, N4IRS; Jonathan Naylor, G4KLX; Hans Barthen, DL5DI; Torsten Shultze, DG1HT'
__license__    = 'GNU GPLv3'
__maintainer__ = 'Cort Buffington, N0MJS'
__email__      = 'n0mjs@me.com'
__status__     = 'pre-alpha'
__version__    = '20170620-py3'

mutex = Lock()  # Used to synchronize Peer I/O in different threads

class TRANSLATE:
    def __init__(self, config_file):
        self.translate = {}
        self.load_config(config_file)
        
    def add_rule(self, tg, export_rule):
        self.translate[str(tg)] = export_rule

    def delete_rule(self, tg):
        if str(tg) in self.translate:
            del self.translate[str(tg)]

    def find_rule(self, tg, slot):
        if str(tg) in self.translate:
            return self.translate[str(tg)]
        return (tg, slot)

    def load_config(self, config_file):
        # Placeholder logic from original file
        print(f'load config file {config_file}')

# translation structure.
translate = TRANSLATE('config.file')

class HB_BRIDGE(HBSYSTEM):
    
    def __init__(self, _name, _config, _logger):
        HBSYSTEM.__init__(self, _name, _config, _logger)

        self._ambeRxPort = 31003        # Port to listen on for AMBE frames to transmit to all peers
        self._gateway = "127.0.0.1"     # IP address of Analog_Bridge app
        self._gateway_port = 31000      # Port Analog_Bridge is listening on for AMBE frames to decode

        self.load_configuration(cli_args.BRIDGE_CONFIG_FILE)

        self.hb_ambe = AMBE_HB(self, _name, _config, _logger, self._ambeRxPort)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def get_globals(self):
        return (subscriber_ids, talkgroup_ids, peer_ids)

    def get_repeater_id(self, import_id):
        if self._config['MODE'] == 'CLIENT':
            return self._config['RADIO_ID']
        return import_id

    # Load configuration from file
    def load_configuration(self, _file_name):
        config = configparser.ConfigParser()
        if not config.read(_file_name):
            sys.exit(f"Configuration file '{_file_name}' is not a valid configuration file! Exiting...")
        try:
            for section in config.sections():
                if section == 'DEFAULTS':
                    self._ambeRxPort = int(config.get(section, 'fromGatewayPort').split(None)[0])
                    self._gateway = config.get(section, 'gateway').split(None)[0]
                    self._gateway_port = int(config.get(section, 'toGatewayPort').split(None)[0])
                if section == 'RULES':
                    for rule in config.items(section):
                        _old_tg, _new_tg, _new_slot = rule[1].split(',')
                        translate.add_rule(hex_str_3(int(_old_tg)), (hex_str_3(int(_new_tg)), int(_new_slot)))

        except configparser.Error:
            traceback.print_exc()
            sys.exit(f'Could not parse configuration file, {_file_name}, exiting...')

    # HBLink callback with DMR data from peer/master.
    def dmrd_received(self, _radio_id, _rf_src, _dst_id, _seq, _slot, _call_type, _frame_type, _dtype_vseq, _stream_id, _data):
        _dst_id, _slot = translate.find_rule(_dst_id, _slot)
        _tx_slot = self.hb_ambe.tx[_slot]
        
        # In Python 3, indexing bytes returns an int, so ord() is often unnecessary 
        # but kept here for logical consistency if _data is treated as a list.
        _seq = _data[4] if isinstance(_data[4], int) else ord(_data[4])
        
        _tx_slot.frame_count += 1
        if (_stream_id != _tx_slot.stream_id):
            self.hb_ambe.begin_call(_slot, _rf_src, _dst_id, _radio_id, _tx_slot.cc, _seq, _stream_id)
            _tx_slot.lastSeq = _seq
        
        if (_frame_type == hb_const.HBPF_DATA_SYNC) and (_dtype_vseq == hb_const.HBPF_SLT_VTERM) and (_tx_slot.type != hb_const.HBPF_SLT_VTERM):
            self.hb_ambe.end_call(_tx_slot)
            
        # Proper bitwise check for Python 3 bytes
        _bits = _data[15] if isinstance(_data[15], int) else ord(_data[15])
        if (_bits & 0x20) == 0:
            _dmr_frame = BitArray('0x' + ahex(_data[20:]).decode('ascii'))
            _ambe = _dmr_frame[0:108] + _dmr_frame[156:264]
            self.hb_ambe.export_voice(_tx_slot, _seq, _ambe.tobytes())
        else:
            _tx_slot.lastSeq = _seq

    def send_master(self, _packet):
        with mutex:
            HBSYSTEM.send_master(self, _packet)
    
    def send_clients(self, _packet):
        with mutex:
            HBSYSTEM.send_clients(self, _packet)

if __name__ == '__main__':
    import argparse
    import os
    import signal
    from dmr_utils.utils import try_download, mk_id_dict
    
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CONFIG_FILE', help='/full/path/to/config.file (default hblink.cfg)')
    parser.add_argument('-l', '--logging', action='store', dest='LOG_LEVEL', help='Override config file logging level.')
    parser.add_argument('-b','--bridge_config', action='store', dest='BRIDGE_CONFIG_FILE', help='/full/path/to/bridgeconfig.cfg (default HB_Bridge.cfg)')
    cli_args = parser.parse_args()

    if not cli_args.CONFIG_FILE:
        cli_args.CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hblink.cfg')

    if not cli_args.BRIDGE_CONFIG_FILE:
        cli_args.BRIDGE_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'HB_Bridge.cfg')

    CONFIG = hb_config.build_config(cli_args.CONFIG_FILE)
    
    if cli_args.LOG_LEVEL:
        CONFIG['LOGGER']['LOG_LEVEL'] = cli_args.LOG_LEVEL
    logger = hb_log.config_logging(CONFIG['LOGGER'])
    
    def sig_handler(_signal, _frame):
        logger.info('SHUTDOWN: HB_Bridge IS TERMINATING WITH SIGNAL %s', str(_signal))
        hblink_handler(_signal, _frame, logger)
        reactor.stop()
        
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, sig_handler)
    
    if CONFIG['ALIASES'].get('TRY_DOWNLOAD'):
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'], CONFIG['ALIASES']['PEER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'], CONFIG['ALIASES']['SUBSCRIBER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        
    peer_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'])
    subscriber_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'])
    talkgroup_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['TGID_FILE'])
    
    logger.info('HBlink \'HB_Bridge.py\' (c) 2017 Mike Zingman N4IRR, N0MJS - SYSTEM STARTING...')
    logger.info('Version %s', __version__)
    
    for system in CONFIG['SYSTEMS']:
        if CONFIG['SYSTEMS'][system]['ENABLED']:
            systems[system] = HB_BRIDGE(system, CONFIG, logger)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['IP'])

    reactor.run()