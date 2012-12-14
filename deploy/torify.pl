#!/usr/bin/perl -w

my $socks_host = shift;
my $socks_port = shift;
my $prog = shift;

if(!defined($socks_host) ||
   !defined($socks_port) ||
   !defined($prog)) {
	print STDERR "Arguments: <socks host> <socks port> <'command [args]'>\n";
	exit;
}

my $rand_socks_file = "/tmp/";

for(my $i = 0; $i < 12; $i++) {
	$rand_socks_file .= ("a".."z")[rand 26];
}
$rand_socks_file .= "-tor-tsocks.conf";

open(FD, ">$rand_socks_file") 
	or die "Cannot open file $rand_socks_file";

print FD "server = $socks_host\n";
print FD "server_port = $socks_port\n";
print FD "local = 127.0.0.0/255.128.0.0\n";
print FD "local = 127.128.0.0/255.192.0.0\n";
print FD "local = $socks_host/255.255.255.255\n";

close(FD);

my $cmd = "TSOCKS_CONF_FILE=$rand_socks_file tsocks $prog";

system("$cmd");
system("rm -f $rand_socks_file");
