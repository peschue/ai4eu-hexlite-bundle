import os
import io
import logging
import json
import time
import grpc
import subprocess
import tempfile
import traceback
import contextlib
import concurrent.futures
import threading
from typing import List, Tuple

import hexlite_pb2 as pb
import hexlite_pb2_grpc as pb_grpc


logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
# logger.basicConfig(level=logging.DEBUG)


class FileParameter:
    filename: str
    filecontent: bytes

    def __repr__(self):
        return "filename=%s filecontent=%s..." % (self.filename, self.filecontent[:10])


class GRPCServicer(pb_grpc.HexliteAnswerSetSolverServicer):
    def __init__(self, config):
        # for debugging you want to set this to True
        self.delete_temporary_directories = True

        self.executable = config['executable']
        self.builtin_plugins_plugindir = config['builtin_plugins_plugindir']

    @contextlib.contextmanager
    def _temporary_directory_context(self):
        if self.delete_temporary_directories:
            with tempfile.TemporaryDirectory() as tempfile_name:
                yield tempfile_name
        else:
            tempfile_name = tempfile.mkdtemp()
            logging.warning("WARNING: self.delete_temporary_directories == False remove directory of this run with    rm -rf %s    ", tempfile_name)
            yield tempfile_name

    def solve(self, request: pb.SolverJob, context) -> pb.SolveResultAnswersets:

        logging.info("ENTRY solve: %s", request)

        ret = pb.SolveResultAnswersets()
        ret.description.code = 0  # no meaning
        ret.description.success = False  # failsafe

        try:
            execution_parameters, file_parameters = self._identify_parameters(request.parameters)

            with self._temporary_directory_context() as tempdir:
                self._prepare_files(tempdir, request.program, file_parameters)

                for answerset in self._execute_hexlite_and_yield_answersets(
                    tempdir,
                    execution_parameters,
                    ret.description.messages
                ):
                    logging.debug("got answer set %s", answerset)
                    ret.answers.append(answerset)

            logging.info("finished: %d answers", len(ret.answers))

            ret.description.success = False

        except Exception as e:
            ret.description.messages.append(
                "Exception: %s\n%s" % (e, traceback.format_exc())
            )

        return ret

    def _identify_parameters(
        self,
        parameters: pb.Parameters
    ) -> Tuple[pb.Parameters, List[FileParameter]]:

        logging.info("ENTRY _identify_parameters %s", parameters)

        pret = pb.Parameters()
        pret.number_of_answers = parameters.number_of_answers
        pret.return_only_optimal_answers = parameters.return_only_optimal_answers

        fret = []

        for p in parameters.additional_parameters:
            if p.key.startswith('file:'):
                # create a file entry
                fp = FileParameter()
                fp.filename = p.key[5:]
                fp.filecontent = p.value.encode('utf8')
                fret.append(fp)
            else:
                # just copy the parameter
                pret.additional_parameters.append(p)

        logging.info("EXIT _identify_parameters %s, %s", pret, fret)

        return (pret, fret)

    def _prepare_files(self, dir: str, program:str, files: List[FileParameter]):

        logging.info("ENTRY _prepare_files dir=%s len(program)=%s files=%s", dir, len(program), [p.filename for p in files])
        for fp in files:
            with open(os.path.join(dir, fp.filename), 'w+b') as f:
                f.write(fp.filecontent)

        with open(os.path.join(dir, 'program.hex'), 'w+t') as f:
            f.write(program)

    def _execute_hexlite_and_yield_answersets(self, dir: str, parameters: pb.Parameters, messages_out: List[str]):

        cmdline = [
            self.executable,
            '--number=%d' % parameters.number_of_answers,
        ]

        for p in parameters.additional_parameters:
            if p.value != '':
                cmdline.append('%s=%s' % (p.key, p.value))
            else:
                cmdline.append(p.key)

        # in addition we want JSON output
        cmdline.extend([
            '--pluginpath=' + self.builtin_plugins_plugindir,
            '--plugin=jsonoutputplugin'
        ])

        # end options and add program
        cmdline.extend([
            '--',
            os.path.join(dir, 'program.hex')
        ])

        p = subprocess.Popen(cmdline, cwd=dir, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')

        def stderr_to_log_and_messages(stderr: io.IOBase, messages: List[str]):
            logging.debug("ENTRY stderr_to_log_and_messages")

            while stderr.readable() and not stderr.closed:
                l = stderr.readline().strip()
                if l == '':
                    break

                messages.append(l)
                logging.info("STDERR: %s", l)

            logging.debug("EXIT stderr_to_log_and_messages")

        # read stderr to logging and to messages
        t = threading.Thread(target=stderr_to_log_and_messages, args=(p.stderr, messages_out), daemon=True)
        t.start()

        while p.stdout.readable() and not p.stdout.closed:
            l = p.stdout.readline()
            if l == '':
                break

            jl = json.loads(l)

            yield self._interpret_json_answerset(jl)

    def _interpret_json_answerset(self, jl: dict):
        ret = pb.Answerset()

        for c in jl['cost']:
            ret.costs.append(pb.CostElement(
                level=c['priority'],
                cost=c['cost']
            ))

        if len(jl['cost']) == 0:
            ret.is_known_optimal = True

        ret.atoms.extend(jl['stratoms'])

        return ret


configfile = os.environ['CONFIG'] if 'CONFIG' in os.environ else "config.json"
logging.info("loading config from %s", configfile)
config = json.load(open(configfile, 'rt'))
grpcserver = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
pb_grpc.add_HexliteAnswerSetSolverServicer_to_server(GRPCServicer(config), grpcserver)
grpcport = config['grpcport']
# listen on all interfaces (otherwise docker cannot export)
grpcserver.add_insecure_port('0.0.0.0:' + str(grpcport))
logging.info("starting grpc server at port %d", grpcport)
grpcserver.start()

while True:
    time.sleep(1)
