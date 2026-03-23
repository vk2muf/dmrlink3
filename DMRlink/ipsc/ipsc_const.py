# Copyright (c) 2013 - 2015 Cortney T. Buffington, N0MJS and the K0USY Group. n0mjs@me.com
#
# This work is licensed under the Creative Commons Attribution-ShareAlike
# 3.0 Unported License.To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View,
# California, 94041, USA.

# Known IPSC Message Types (Converted to Bytes for Python 3)
CALL_CONFIRMATION     = b'\x05' # Confirmation FROM the recipient of a confirmed call.
TXT_MESSAGE_ACK       = b'\x54' # Doesn't seem to mean success, though.
CALL_MON_STATUS       = b'\x61' 
CALL_MON_RPT          = b'\x62' 
CALL_MON_NACK         = b'\x63' 
XCMP_XNL              = b'\x70' # XCMP/XNL control message
GROUP_VOICE           = b'\x80'
PVT_VOICE             = b'\x81'
GROUP_DATA            = b'\x83'
PVT_DATA              = b'\x84'
RPT_WAKE_UP           = b'\x85' # Similar to OTA DMR "wake up"
UNKNOWN_COLLISION     = b'\x86' # Seen when two dmrlinks try to transmit at once
MASTER_REG_REQ        = b'\x90' # FROM peer TO master
MASTER_REG_REPLY      = b'\x91' # FROM master TO peer
PEER_LIST_REQ         = b'\x92' # From peer TO master
PEER_LIST_REPLY       = b'\x93' # From master TO peer
PEER_REG_REQ          = b'\x94' # Peer registration request
PEER_REG_REPLY        = b'\x95' # Peer registration reply
MASTER_ALIVE_REQ      = b'\x96' # FROM peer TO master
MASTER_ALIVE_REPLY    = b'\x97' # FROM master TO peer
PEER_ALIVE_REQ        = b'\x98' # Peer keep alive request
PEER_ALIVE_REPLY      = b'\x99' # Peer keep alive reply
DE_REG_REQ            = b'\x9A' # Request de-registration from system
DE_REG_REPLY          = b'\x9B' # De-registration reply

# IPSC Version Information
IPSC_VER_14           = b'\x00'
IPSC_VER_15           = b'\x00'
IPSC_VER_15A          = b'\x00'
IPSC_VER_16           = b'\x01'
IPSC_VER_17           = b'\x02'
IPSC_VER_18           = b'\x02'
IPSC_VER_19           = b'\x03'
IPSC_VER_22           = b'\x04'

# Link Type Values
LINK_TYPE_IPSC        = b'\x04'

# Burst Data Types
BURST_DATA_TYPE = {
    'VOICE_HEAD':  b'\x01',
    'VOICE_TERM':  b'\x02',
    'SLOT1_VOICE': b'\x0A',
    'SLOT2_VOICE': b'\x8A'   
}

# IPSC Version and Link Type are concatenated as bytes
IPSC_VER = LINK_TYPE_IPSC + IPSC_VER_17 + LINK_TYPE_IPSC + IPSC_VER_16

# Packets that must originate from a peer
ANY_PEER_REQUIRED = [GROUP_VOICE, PVT_VOICE, GROUP_DATA, PVT_DATA, CALL_MON_STATUS, CALL_MON_RPT, CALL_MON_NACK, XCMP_XNL, RPT_WAKE_UP, DE_REG_REQ]

# Packets that must originate from a non-master peer
PEER_REQUIRED = [PEER_ALIVE_REQ, PEER_ALIVE_REPLY, PEER_REG_REQ, PEER_REG_REPLY]

# Packets that must originate from a master peer
MASTER_REQUIRED = [PEER_LIST_REPLY, MASTER_ALIVE_REPLY]

# User-Generated Packet Types
USER_PACKETS = [GROUP_VOICE, PVT_VOICE, GROUP_DATA, PVT_DATA]

# RCM (Repeater Call Monitor) Constants
TS = {
    b'\x00': '1',
    b'\x01': '2'
}

NACK = {
    b'\x05': 'BSID Start',
    b'\x06': 'BSID End'
}

TYPE = {
    b'\x30': 'Private Data Set-Up',
    b'\x31': 'Group Data Set-Up',
    b'\x32': 'Private CSBK Set-Up',
    b'\x45': 'Call Alert',
    b'\x47': 'Radio Check Request',
    b'\x48': 'Radio Check Success',
    b'\x49': 'Radio Disable Request',
    b'\x4A': 'Radio Disable Received',
    b'\x4B': 'Radio Enable Request',
    b'\x4C': 'Radio Enable Received',
    b'\x4D': 'Remote Monitor Request',
    b'\x4E': 'Remote Monitor Request Received',
    b'\x4F': 'Group Voice',
    b'\x50': 'Private Voice',
    b'\x51': 'Group Data',
    b'\x52': 'Private Data',
    b'\x53': 'All Call',
    b'\x54': 'Message ACK/Failure',
    b'\x84': 'ARS/GPS?'
}

SEC = {
    b'\x00': 'None',
    b'\x01': 'Basic',
    b'\x02': 'Enhanced'
}

STATUS = {
    b'\x01': 'Active',
    b'\x02': 'End',
    b'\x05': 'TS In Use',
    b'\x08': 'RPT Disabled',
    b'\x09': 'RF Interference',
    b'\x0A': 'BSID ON',
    b'\x0B': 'Timeout',
    b'\x0C': 'TX Interrupt'
}

REPEAT = {
    b'\x01': 'Repeating',
    b'\x02': 'Idle',
    b'\x03': 'TS Disabled',
    b'\x04': 'TS Enabled'
}