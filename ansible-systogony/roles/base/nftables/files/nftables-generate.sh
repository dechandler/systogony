#!/bin/bash

CONF="/etc/nftables/assembled.conf"

echo '' > $CONF
chmod 600 $CONF

cat << EOF >> $CONF
#!/usr/sbin/nft -f

flush ruleset

table inet global {

    chain PREROUTING {
        type filter hook prerouting priority filter; policy accept;
        icmpv6 type { nd-router-advert, nd-neighbor-solicit } accept
        meta nfproto ipv6 fib saddr . mark . iif oif missing drop

EOF

cat /etc/nftables/prerouting.d/*.conf >> $CONF

cat << EOF >> $CONF
    }

    chain INPUT {
        type filter hook input priority filter; policy accept;
        ct state { established, related } accept
        ct status dnat accept
        iifname "lo" accept
        ct state invalid drop

EOF

cat /etc/nftables/input.d/*.conf >> $CONF


cat << EOF >> $CONF

        reject with icmpx admin-prohibited
    }

    chain FORWARD {
        type filter hook forward priority filter; policy accept;
        ct state { established, related } accept
        ct status dnat accept
        iifname "lo" accept
        ct state invalid drop
        ip6 daddr { ::/96, ::ffff:0.0.0.0/96, 2002::/24, 2002:a00::/24, 2002:7f00::/24, 2002:a9fe::/32, 2002:ac10::/28, 2002:c0a8::/32, 2002:e000::/19 } reject with icmpv6 addr-unreachable

EOF

cat /etc/nftables/forward.d/*.conf >> $CONF

cat << EOF >> $CONF

        reject with icmpx admin-prohibited
    }

    chain OUTPUT {
        type filter hook output priority filter; policy accept;
        ct state { established, related } accept
        oifname "lo" accept
        ip6 daddr { ::/96, ::ffff:0.0.0.0/96, 2002::/24, 2002:a00::/24, 2002:7f00::/24, 2002:a9fe::/32, 2002:ac10::/28, 2002:c0a8::/32, 2002:e000::/19 } reject with icmpv6 addr-unreachable

EOF

cat /etc/nftables/output.d/*.conf >> $CONF

cat << EOF >> $CONF

    }

    chain NAT_PREROUTING {
        type nat hook prerouting priority -100

EOF

cat /etc/nftables/nat-prerouting.d/*.conf >> $CONF

cat << EOF >> $CONF

    }

    chain NAT_POSTROUTING {
        type nat hook postrouting priority -100

EOF

cat /etc/nftables/nat-postrouting.d/*.conf >> $CONF


cat << EOF >> $CONF

    }

}

EOF
