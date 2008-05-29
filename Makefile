CFLAGS=-Wall -Wshadow -Wpointer-arith -Wcast-qual -Wcast-align \
	-Wwrite-strings -Wconversion -Waggregate-return \
	-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations \
	-Wredundant-decls -Wnested-externs -Werror

tool := postconfirm

include ../Makefile.common

% : %.c
	$(CC) $(CFLAGS) -o $@ $(LDFLAGS) $<

