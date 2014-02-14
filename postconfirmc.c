/* $Id: readyexec.c,v 1.7 2002/10/09 20:16:28 ftobin Exp $ */
// Copied with slight modifications from Frank Tobin's 'readyexec.c'

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sysexits.h>
#include <unistd.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/uio.h>

#define PROGNAME "postconfirm"
#define DEBUG    0

#define DO_SEND_ARGS     1
#define DO_SEND_ENV      1
#define DO_SEND_FD_NAMES 1

#define debug fprintf
#define SOCK_PATH	"/var/run/postconfirm/socket"
#define SOCK_BUF_LEN	256
#define MY_ARGC 1

void error(const char *msg);
void myclose(FILE *stream);
int  myconnect(const char *path);
void myflush(FILE *stream);
void proto_error(const char *msg);
int  read_exit_code(FILE *stream);
void send_args(FILE *stream, int argc, char **argv);
void usage(void);
void verify_expected(FILE *stream, const char *expected);

void  write_netstring(FILE *stream, const void *ptr, size_t len);
char* read_netstring(FILE *stream, size_t *len_ptr);
void  write_netstring_nulled(FILE *stream, const char *ptr);

void write_netint(FILE *stream, int len);
int read_netint(FILE *stream);

void send_fd(int s, int fd);
void send_named_fd(FILE *stream, const char *name, int fd);

void send_env(FILE *stream);
int count_env(void);

extern char **environ;

FILE *debugf;
int  do_debug;

int main(int argc, char **argv)
{
    int cs; /* control socket */
    short int send_stop;
    char sock_path[SOCK_BUF_LEN];
    int i;
    
    FILE *csfile;
    
    debugf = DEBUG ? stderr : fopen("/dev/null", "w");
    
    // default values
    send_stop = 0;
    strncpy(sock_path, SOCK_PATH, SOCK_BUF_LEN);

    for (i = 1; i < argc; i++) {
	if (strcmp("--stop", argv[i]) == 0) { send_stop = 1; }
	if (strcmp("--socket", argv[i]) == 0) {
	    i++;
	    if (i < argc) {
		strncpy(sock_path, argv[i], SOCK_BUF_LEN);
	    } else {
		error("missing argument to --socket");
	    }
	}
    }
    
    cs = myconnect(sock_path);
    
    csfile = fdopen(cs, "w+");
    if (!csfile) { error("fdopen of socket"); }

    if (send_stop)
    {
	write_netstring_nulled(csfile, "stop");
	return 0;
    }
    else
    {
	write_netstring_nulled(csfile, "conduit");
    }
    
    if (DO_SEND_ARGS)
    {
	debug(debugf, "sending args\n");
	send_args(csfile, argc, argv);
    }
    
    if (DO_SEND_ENV)
    {
	debug(debugf, "sending environment\n");
	send_env(csfile);
    }

    send_named_fd(csfile, "stdin",  STDIN_FILENO);
    send_named_fd(csfile, "stdout", STDOUT_FILENO);
    send_named_fd(csfile, "stderr", STDERR_FILENO);
    
    if (shutdown(cs, SHUT_WR) == -1) { error("shutdown"); }
    
    debug(debugf, "reading exit code\n");
    return read_exit_code(csfile);
}


void myflush(FILE *stream)
{
    if (fflush(stream) != 0)  { error("fflush"); }
}


void myclose(FILE *stream)
{
    if (fclose(stream) != 0)  { error("fclose"); }
}


int myconnect(const char *path)
{
    struct sockaddr_un saddr;
    int s;
    
    strncpy(saddr.sun_path, path, sizeof(saddr.sun_path));
    saddr.sun_family = AF_UNIX;
    
    s = socket(PF_UNIX, SOCK_STREAM, 0);
    if (s == -1) { error("socket"); }
    
    if (connect(s, (struct sockaddr *)&saddr, sizeof(saddr)) == -1)
    {
	error("connect");
    }
    
    return s;
}


void send_args(FILE *stream, int argc, char **argv)
{
    int i;
    
    write_netstring_nulled(stream, "args");
    write_netint(stream, argc - MY_ARGC);
    
    for (i = MY_ARGC; i < argc; i++)
    {
	write_netstring_nulled(stream, argv[i]);
    }
}


void send_named_fd(FILE *stream, const char *name, int fd)
{
    debug(debugf, "sending %s descriptor\n", name);

    if (DO_SEND_FD_NAMES)
    {
	write_netstring_nulled(stream, name);
    }
    
    myflush(stream);
    send_fd(fileno(stream), fd);
}


void send_env(FILE *stream)
{
    int i;
    int count;
    
    write_netstring_nulled(stream, "env");
    count = count_env();
    debug(debugf, "counted %d environment variables\n", count);
    write_netint(stream, count);
    
    for (i = 0; i < count; i++)
    {
	write_netstring_nulled(stream, environ[i]);
    }    
}


int count_env()
{
    int i;
    i = 0;
    
    while (environ[i] != NULL)
    {
	i++;
    }
    
    return i;
}


int read_exit_code(FILE *stream)
{
    int i;
    verify_expected(stream, "exit");
    i = read_netint(stream);
    debug(debugf, "read exit code of %d\n", i);
    return i;
}


void write_netstring_nulled(FILE *stream, const char *ptr)
{
    debug(debugf, "sending string '%s'\n", ptr);
    write_netstring(stream, ptr, strlen(ptr));
}


/* netstrings: http://cr.yp.to/proto/netstrings.txt */
void write_netstring(FILE *stream, const void *ptr, size_t len)
{
    char buff[64] = {0};
    
    snprintf(buff, sizeof(buff), "%s", (const char *)ptr);
    
    if (fprintf(stream, "%ld:", len) == 0) { error("fprintf"); }
    if (fwrite(ptr, 1, len, stream) < 1)   { error("fwrite"); }
    if (fputc(',', stream) == EOF)         { error("fputc"); }
}


void write_netint(FILE *stream, int l)
{
    debug(debugf, "sending netint %d\n", l);
    if (fprintf(stream, "%d,", l) == 0) { error("fprintf of netint"); }
}


int read_netint(FILE *stream)
{
    int i;
    char error_buf[256] = {0};
    char error_buf2[256] = {0};

    if (fscanf(stream, "%d,", &i) < 1)
    {
	fread(error_buf2, 10, 1, stream);
	snprintf(error_buf, sizeof(error_buf),
		 "netint (%s) is invalid", error_buf2);
	proto_error(error_buf);
    }
    
/* debug(debugf, "read a netint of %d\n", i); */
    return i;
}


/* netstrings: http://cr.yp.to/proto/netstrings.txt */
/* bonus: I null-terminate */
char* read_netstring(FILE *stream, size_t *len_ptr)
{
    char error_buf[256] = {0};
    char error_buf2[256] = {0};
    char *buf;
    int c;
    int num_read;
    
    num_read = fscanf(stream, "%4ld:", len_ptr);
    if (num_read < 1)
    {
	if (num_read == EOF) { proto_error("EOF during netstring length"); }
	
	fread(error_buf2, 10, 1, stream);
	snprintf(error_buf, sizeof(error_buf),
		 "netstring length (%s) is invalid",
		 error_buf2);
	proto_error(error_buf);
    }
    
    buf = malloc(*len_ptr + 1); /* malloc(0) is not portable
				   and I want it null terminated */
    
    if (!buf)                                { error("malloc"); }
    bzero(buf, *len_ptr +1);
    if (fread(buf, 1, *len_ptr, stream) < 1) { error("fread"); }
    
    c = fgetc(stream);
    if (c != ',')
    {
	snprintf(error_buf, sizeof(error_buf),
		 "netstring %s (length %ld) incorrectly terminated: expected comma, got %c",
		 buf, *len_ptr, c);
	proto_error(error_buf);
    }
    
    return buf;
}


void verify_expected(FILE *stream, const char *expected)
{
    char *got;
    size_t len;
    char buff[256] = {0}; /* meant for error messages */
    
    got = read_netstring(stream, &len);
    if (strcmp(expected, got) != 0)
    {
	snprintf(buff, sizeof(buff), "expected %s, got %s",
		 expected, got);
	proto_error(buff);
    }
    
    free(got);
}


void usage(void)
{
    fprintf(stderr, "usage: %s [--stop] [args]\n", PROGNAME);
    exit(EX_USAGE);
}


void error(const char *msg)
{
    perror(msg);
    exit(EX_OSERR);
}


void proto_error(const char *msg)
{
    fprintf(stderr, "%s: %s: protocol error\n", PROGNAME, msg);
    exit(EX_PROTOCOL);
}


void send_fd(int s, int fd)
{
    struct msghdr   msg = {0};
    struct cmsghdr *cmsg;
    struct iovec    iov[1];
    
    char buf[CMSG_SPACE(sizeof(fd))] = {0};  /* ancillary data buffer */
    char identifier[] = {'X'};   /* baggage to help blocking kick in? */
    
    msg.msg_control    = buf;
    msg.msg_controllen = sizeof(buf);
    
    /* trying to send some bytes with it to help blocking kick in? */
    msg.msg_iovlen  = 1;
    msg.msg_iov     = iov;
    iov[0].iov_len  = sizeof(identifier);
    iov[0].iov_base = identifier;
    
    cmsg             = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_len   = CMSG_LEN(sizeof(fd));
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type  = SCM_RIGHTS;
    
    *(int *)CMSG_DATA(cmsg) = fd;
    
    if (sendmsg(s, &msg, 0) != sizeof(identifier))
    {
	error("sendmsg");
    }
}
