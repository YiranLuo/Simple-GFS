import zerorpc


class ZClient:

    def __init__(self, ip='localhost', port=1400):
        self.master = zerorpc.Client()
        address = 'tcp://%s:%s' % (ip, str(port))
        print 'Connecting to master at %s' % address
        self.master.connect(address)

    def close(self):
        """Closes connection with master"""
        self.master.close()

    def write(self, filename, data):
        """
        Creates a new file, writes the data
        :param filename:
        :param data:
        """
        # to be implemented
        '''if self._exists(filename):
            self.delete(filename)'''

        num_chunks = self._num_chunks(len(data))
        chunkuuids = self.master.alloc(filename, num_chunks)
        self._write_chunks(chunkuuids, data)

    def _exists(self, filename):
        return self.master.exists(filename)

    def _num_chunks(self, size):
        chunksize = self.master.get('chunksize')
        return (size // chunksize) + (1 if size % chunksize > 0 else 0)

    def _write_chunks(self, chunkuuids, data):
        chunksize = self.master.get('chunksize')
        chunks = [data[x:x+chunksize] for x in range(0, len(data), chunksize)]

        # connect with each chunkserver. Change to check/establish later
        chunkserver_clients = self._establish_connection()

        # write to each chunkserver
        for idx, chunkuuid in enumerate(chunkuuids):
            chunkloc = self.master.get_chunkloc(chunkuuid)
            chunkserver_clients[chunkloc].write(chunkuuid, chunks[idx])

    def _establish_connection(self):
        """
        Creates zerorpc client for each chunkserver
        :return:  Dictionary of zerorpc clients bound to chunkservers
        """
        chunkserver_client = {}
        chunkservers = self.master.get('chunkservers')

        for idx in range(len(chunkservers)):
            zclient = zerorpc.Client()
            print 'Client connecting to chunkserver at %s' % chunkservers[idx]
            zclient.connect(chunkservers[idx])
            zclient.print_name()
            chunkserver_client[idx] = zclient

        return chunkserver_client

    def list(self):
        filelist = self.master.list()
        if filelist:
            for file in filelist:
                print file
        else:
            print 'No files in the system.'

    def read(self, filename):  # get metadata, then read chunks direct
        """
        Connects to each chunkserver and reads the chunks in order, then
        assembles the file by reducing
        :param filename:
        :return:  file contents
        """
        if not self._exists(filename):
            raise Exception("read error, file does not exist: " + filename)
        chunks = []
        chunkuuids = self.master.get_chunkuuids(filename)
        chunkserver_clients = self._establish_connection()
        for chunkuuid in chunkuuids:
            chunkloc = self.master.get_chunkloc(chunkuuid)
            chunk = chunkserver_clients[chunkloc].read(chunkuuid)
            chunks.append(chunk)
        data = reduce(lambda x, y: x + y, chunks)  # reassemble in order
        return data

    def dump_metadata(self):
        self.master.dump_metadata()

    def append(self, filename, data):
        if not self._exists(filename):
            raise Exception("append error, file does not exist: " + filename)
        num_chunks = self._num_chunks(len(data))
        append_chunkuuids = self.master.alloc_append(filename, num_chunks)
        self._write_chunks(append_chunkuuids, data)

    def delete(self, filename):
        self.master.delete(filename)
