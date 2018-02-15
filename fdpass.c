/* $Id: fdpass.c,v 1.11 2002/08/14 00:16:09 ftobin Exp $ */

/*  Thanks to Tres Seaver, tseaver@starbase.neosoft.com, for example code
    http://mail.python.org/pipermail/python-list/1999-October/013241.html
*/

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/uio.h>

#include <Python.h>

static PyObject* send_fd(PyObject *self, PyObject *args);
static PyObject* recv_fd(PyObject *self, PyObject *args);

void initfdpass(void);


static PyMethodDef Methods[] = {
    {"send_fd",  send_fd, METH_VARARGS,
     "send_fd(socket, fd) -> None\nSend fd through socket.  socket is an int.\nSends 1 byte of payload (in one iovec array)."},
    
    {"recv_fd",  recv_fd, METH_VARARGS,
     "recv_fd(socket) -> fd\nRead a fd from socket.  socket is an int.\nExpects to read 1 byte of payload (in one iovec array)."},
    
    {NULL, NULL, 0, NULL}        /* Sentinel */
};



void initfdpass(void)
{
    (void) Py_InitModule("fdpass", Methods);
}


static PyObject* send_fd(PyObject *self, PyObject *args)
{
    struct msghdr   msg = {0};
    struct cmsghdr *cmsg;
    struct iovec    iov[1];
    
    char buf[CMSG_SPACE(sizeof(int))] = {0};  /* ancillary data buffer */
    char identifier[] = {'X'};

    int  socket;
    int  fd;
    
    if (!PyArg_ParseTuple(args, "ii", &socket, &fd))
    {
	return NULL;
    }
    
    /* trying to send some bytes with it to help blocking kick in */
    msg.msg_iovlen  = 1;
    msg.msg_iov     = iov;
    iov[0].iov_len  = sizeof(identifier);
    iov[0].iov_base = identifier;

    msg.msg_control    = buf;
    msg.msg_controllen = sizeof(buf);
    
    cmsg             = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_len   = CMSG_LEN(sizeof(fd));
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type  = SCM_RIGHTS;
    
    /* Initialize the payload: */
    *(int *)CMSG_DATA(cmsg) = fd;
    
    if (sendmsg(socket, &msg, 0) != sizeof(identifier))
    {
	return PyErr_SetFromErrno(PyExc_OSError);
    }
    
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject* recv_fd(PyObject *self, PyObject *args)
{
    struct msghdr   msg = {0};
    struct cmsghdr *cmsg;
    struct iovec    iov[1];
    
    char buf[CMSG_SPACE(sizeof(int))] = {0};  /* ancillary data buffer */
    char iov_base_buf[1] = {0};

    int  socket;
    ssize_t  recv_bytes;
    
    /* ensure we get no args */
    if (!PyArg_ParseTuple(args, "i", &socket))
    {
	return NULL;
    }
    
    msg.msg_control    = buf;
    msg.msg_controllen = sizeof(buf);
    msg.msg_iov        = iov;
    msg.msg_iovlen     = 1;
    iov[0].iov_len     = sizeof(iov_base_buf);
    iov[0].iov_base    = iov_base_buf;
    
    recv_bytes = recvmsg(socket, &msg, 0);
    
    if (recv_bytes < 0)
    {
	return PyErr_SetFromErrno(PyExc_OSError);
    }
    
    /* While we technically can receive a message without any
       data attached, for debugging purposes, it's much better
       to just say that we mandate receiving at least a byte
    */
    if (recv_bytes == 0)
    {
	PyErr_SetString(PyExc_EOFError,
			"possibly the sender didn't put any data into the iovec array?");
	return NULL;
    }


    /* XXX: Might realloc, so reseat? */
    cmsg = CMSG_FIRSTHDR( &msg );

    if (cmsg == NULL)
    {
	PyErr_SetString(PyExc_RuntimeError,
			"CMSG_FIRSTHDR() returned NULL; where is the ancillary data?!?");
	return NULL;
    }
    
    if (msg.msg_flags != 0)
    {
	return PyErr_Format(PyExc_RuntimeError,
			    "received message with unexpected msg_flags: expected %#x, got %#x",
			    0, msg.msg_flags);
    }

    if (cmsg->cmsg_level != SOL_SOCKET)
    {
	return PyErr_Format(PyExc_RuntimeError,
			    "received message with unexpected cmsg_level: expected %#x, got %#x",
			    SOL_SOCKET, cmsg->cmsg_level);
    }
    
    if (cmsg->cmsg_type != SCM_RIGHTS)
    {
	return PyErr_Format(PyExc_RuntimeError,
		 "received message with unexpected cmsg_type: expected %#x, got %#x",
		 SCM_RIGHTS, cmsg->cmsg_type);
    }
    
    if (cmsg->cmsg_len != CMSG_LEN(sizeof(int)))
    {
	return PyErr_Format(PyExc_RuntimeError,
		 "received message with unexpected cmsg_len: expected %lu, got %ld",
		 CMSG_LEN(sizeof(int)), cmsg->cmsg_len);
    }

    return Py_BuildValue("i", *(int*)CMSG_DATA( cmsg ));
}
