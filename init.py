'''The Configs are defined here'''

Vendor_to_change = "Dell Inc."
seeddevice="10.0.11.11"

# Check only these Platforms in CDP discovery
platforms = ['cisco C9200', 'cisco C9300', 'cisco C9400', 'cisco C9500', 'cisco C9600', 'cisco WS-C2960', 'cisco WS-3650', 'cisco WS-C3850' ]

# Modify for your need 
dot1x_config = ["switchport mode access",
"switchport port-security maximum 10",
"switchport port-security violation restrict",
"switchport port-security aging time 2",
"switchport port-security aging type inactivity",
"switchport port-security",
"device-tracking attach-policy IPDT_MAX_10",
"no cdp enable",
"authentication periodic",
"authentication timer reauthenticate server",
"access-session control-direction in",
"access-session closed",
"access-session port-control auto",
"mab",
"snmp trap mac-notification change added",
"snmp trap mac-notification change removed",
"dot1x pae authenticator",
"dot1x timeout tx-period 10",
"storm-control broadcast level 7.00 5.00",
"storm-control multicast level 7.00 5.00",
"storm-control action trap",
"spanning-tree portfast",
"service-policy type control subscriber CERAM_DOT1X_MAB"
]
