#!/usr/bin/env python3
#
###############################################################################
#   Copyright (C) 2016  Cortney T. Buffington, N0MJS <n0mjs@me.com>
#   and
#   Copyright (C) 2017  Mike Zingman, N4IRR <Not.A.Chance@NoWhere.com>
#   Converted to Python 3
###############################################################################
# This is a bridge application for IPSC networks.  It knows how to export AMBE
# frames and metadata to an external program/network.  It also knows how to import
# AMBE and metadata from an external network and send the DMR frames to IPSC networks.
###############################################################################

from twisted.internet import reactor
from binascii import b2a_hex as h
from bitstring import BitArray

import sys
import socket
import configparser
import traceback
import pickle 
import _thread as thread
import os
import signal
import argparse
from time import time, sleep, localtime, strftime
import csv
import struct
from random import randint

from dmrlink import IPSC, systems, config_reports, reportFactory 
from dmr_utils.utils import int_id, hex_str_3, hex_str_4, get_alias, get_info
from dmr_utils import ambe_utils
from dmr_utils.ambe_bridge import AMBE_IPSC

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2013 - 2016 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Robert Garcia, N5QM; Steve Zingman, N4IRS; Mike Zingman, N4IRR'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'
__version__     = '20240521-Py3'

try:
    from ipsc.ipsc_const import *
except ImportError:
    sys.exit('IPSC constants file not found or invalid')

try:
    from ipsc.ipsc_mask import *
except ImportError:
    sys.exit('IPSC mask values file not found or invalid')


class ambeIPSC(IPSC):

    _configFile = 'IPSC_Bridge.cfg'
    _gateway = "127.0.0.1"
    _gateway_port = 31000
    _ambeRxPort = 31003
    
    _busy_slots = [0, 0, 0]

    _currentNetwork = ""
    cc = 1

    def __init__(self, _name, _config, _logger, _report):
        IPSC.__init__(self, _name, _config, _logger, _report)
        
        self._currentNetwork = str(_name)
        self.readConfigFile(self._configFile, None, self._currentNetwork)
    
        self._logger.info('DMRLink IPSC Bridge Initialized')
        self.ipsc_ambe = AMBE_IPSC(self, _name, _config, _logger, self._ambeRxPort)

    def get_globals(self):
        return (subscriber_ids, talkgroup_ids, peer_ids)

    def get_repeater_id(self, import_id):
        return self._config['LOCAL']['RADIO_ID']

    def defaultOption(self, config, sec, opt, defaultValue):
        try:
            _value = config.get(sec, opt).split(None)[0]
        except (configparser.NoOptionError, configparser.NoSectionError):
            try:
                _value = config.get('DEFAULTS', opt).split(None)[0]
            except (configparser.NoOptionError, configparser.NoSectionError):
                _value = defaultValue
        self._logger.info('{} = {}'.format(opt, str(_value)))
        return _value

    def readConfigFile(self, configFileName, sec, networkName='DEFAULTS'):
        config = configparser.ConfigParser()
        try:
            config.read(configFileName)
            
            if sec is None:
                sec = self.defaultOption(config, 'DEFAULTS', 'section', networkName)
            if not config.has_section(sec):
                self._logger.info('Section {} was not found, using DEFAULTS'.format(sec))
                sec = 'DEFAULTS'

            self._gateway = self.defaultOption(config, sec, 'gateway', self._gateway)
            self._gateway_port = int(self.defaultOption(config, sec, 'toGatewayPort', self._gateway_port))
            self._ambeRxPort = int(self.defaultOption(config, sec, 'fromGatewayPort', self._ambeRxPort))

        except configparser.NoOptionError as e:
            print('Using a default value:', e)
        except Exception:
            traceback.print_exc()
            sys.exit("Configuration file '{}' is not a valid configuration file! Exiting...".format(configFileName))

    def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        _tx_slot = self.ipsc_ambe.tx[_ts]
        _payload_type = _data[30:31] 
        _seq = int_id(_data[20:22])
        _tx_slot.frame_count += 1
        
        if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
            _stream_id = int_id(_data[5:6])
            if _stream_id != _tx_slot.stream_id:
                self.ipsc_ambe.begin_call(_ts, _src_sub, _dst_sub, _peerid, self.cc, _seq, _stream_id)
            _tx_slot.lastSeq = _seq
            
        if _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
            self.ipsc_ambe.end_call(_tx_slot)
            
        if (_payload_type == BURST_DATA_TYPE['SLOT1_VOICE']) or (_payload_type == BURST_DATA_TYPE['SLOT2_VOICE']):
            _payload_hex = h(_data[33:52]).decode('ascii')
            _ambe_frames = BitArray('0x' + _payload_hex)
            _ambe_frame1 = _ambe_frames[0:49]
            _ambe_frame2 = _ambe_frames[50:99]
            _ambe_frame3 = _ambe_frames[100:149]
            self.ipsc_ambe.export_voice(_tx_slot, _seq, _ambe_frame1.tobytes() + _ambe_frame2.tobytes() + _ambe_frame3.tobytes())

    def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
        print('private voice')

    def dumpIPSCFrame(self, _frame):
        _packettype     = int_id(_frame[0:1])
        _peerid         = int_id(_frame[1:5])
        _ipsc_seq       = int_id(_frame[5:6])
        _src_sub        = int_id(_frame[6:9])
        _dst_sub        = int_id(_frame[9:12])
        _call_type      = int_id(_frame[12:13])
        _call_ctrl_info = int_id(_frame[13:17])
        _call_info      = int_id(_frame[17:18])
        
        _rtp_byte_1 = int_id(_frame[18:19])
        _rtp_byte_2 = int_id(_frame[19:20])
        _rtp_seq    = int_id(_frame[20:22])
        _rtp_tmstmp = int_id(_frame[22:26])
        _rtp_ssid   = int_id(_frame[26:30])
        
        _payload_type   = _frame[30:31]
        _ts             = bool(_call_info & TS_CALL_MSK)
        _end            = bool(_call_info & END_MSK)

        if _payload_type == BURST_DATA_TYPE['VOICE_HEAD']:
            print('HEAD:', h(_frame).decode('ascii'))
            
        elif _payload_type == BURST_DATA_TYPE['VOICE_TERM']:
            _ipsc_rssi_threshold_and_parity = int_id(_frame[31:32])
            _ipsc_length_to_follow = int_id(_frame[32:34])
            _ipsc_rssi_status = int_id(_frame[34:35])
            _ipsc_slot_type_sync = int_id(_frame[35:36])
            _ipsc_data_size = int_id(_frame[36:38])
            _ipsc_data = _frame[38:38 + (_ipsc_length_to_follow * 2) - 4]
            
            print('TERM:', h(_frame).decode('ascii'))
            
        elif _payload_type == BURST_DATA_TYPE['SLOT1_VOICE']:
            print('SLOT1:', h(_frame).decode('ascii'))
        elif _payload_type == BURST_DATA_TYPE['SLOT2_VOICE']:
            print('SLOT2:', h(_frame).decode('ascii'))
            
        print("pt={:02X} pid={} seq={:02X} src={} dst={} ct={:02X} uk={} ci={} rsq={}".format(
            _packettype, _peerid, _ipsc_seq, _src_sub, _dst_sub, _call_type, _call_ctrl_info, _call_info, _rtp_seq))
    
if __name__ == '__main__':
    from dmr_utils.utils import try_download, mk_id_dict
    from ipsc.dmrlink_log import config_logging    
    from ipsc.dmrlink_config import build_config
    
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CFG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    parser.add_argument('-ll', '--log_level', action='store', dest='LOG_LEVEL', help='Override config file logging level.')
    parser.add_argument('-lh', '--log_handle', action='store', dest='LOG_HANDLERS', help='Override config file logging handler.')
    cli_args = parser.parse_args()

    if not cli_args.CFG_FILE:
        cli_args.CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dmrlink.cfg')
    
    CONFIG = build_config(cli_args.CFG_FILE)
    
    if cli_args.LOG_LEVEL:
        CONFIG['LOGGER']['LOG_LEVEL'] = cli_args.LOG_LEVEL
    if cli_args.LOG_HANDLERS:
        CONFIG['LOGGER']['LOG_HANDLERS'] = cli_args.LOG_HANDLERS
    logger = config_logging(CONFIG['LOGGER'])  

    logger.info('DMRlink \'IPSC_Bridge.py\' Python 3 Modernized - SYSTEM STARTING...')
    logger.info('Version %s', __version__)

    if CONFIG['ALIASES'].get('TRY_DOWNLOAD'):
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'], CONFIG['ALIASES']['PEER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        result = try_download(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'], CONFIG['ALIASES']['SUBSCRIBER_URL'], CONFIG['ALIASES']['STALE_TIME'])
        logger.info(result)
        
    peer_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['PEER_FILE'])
    subscriber_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['SUBSCRIBER_FILE'])
    talkgroup_ids = mk_id_dict(CONFIG['ALIASES']['PATH'], CONFIG['ALIASES']['TGID_FILE'])
    
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
        for system in systems:
            this_ipsc = systems[system]
            logger.info('De-Registering from IPSC %s', system)
            de_reg_req_pkt = this_ipsc.hashed_packet(this_ipsc._local['AUTH_KEY'], this_ipsc.DE_REG_REQ_PKT)
            this_ipsc.send_to_ipsc(de_reg_req_pkt)
        reactor.stop()

    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)

    report_server = config_reports(CONFIG, logger, reportFactory)

    for system in CONFIG['SYSTEMS']:
        if CONFIG['SYSTEMS'][system]['LOCAL']['ENABLED']:
            systems[system] = ambeIPSC(system, CONFIG, logger, report_server)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['LOCAL']['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['LOCAL']['IP'])
    
    reactor.run()