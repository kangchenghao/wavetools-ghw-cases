-- SPDX-License-Identifier: MIT
entity cross_format is
    generic (
        marker_rise_ns : positive := 10;
        toggle_flag    : boolean  := false
    );
end entity;

architecture fixture of cross_format is
    type packet_type is record
        valid : bit;
        flag  : bit;
    end record;

    signal marker : bit := '0';
    signal packet : packet_type := ('0', '0');
begin
    marker <= '1' after marker_rise_ns * 1 ns, '0' after 20 ns;
    packet.valid <= '1' after 10 ns, '0' after 20 ns;
    packet.flag <= '1' after 10 ns, '0' after 20 ns when toggle_flag else '0';
end architecture;
