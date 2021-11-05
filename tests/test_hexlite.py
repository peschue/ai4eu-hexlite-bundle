#!/usr/bin/env python3

import logging
import grpc
import json
import os

import hexlite_pb2_grpc as pb_grpc
import hexlite_pb2 as pb

configfile = os.environ.get('CONFIG', "config.json")
config = json.load(open(configfile, 'rt'))

logging.basicConfig(level=logging.DEBUG)


def main():
    channel = grpc.insecure_channel('localhost:%d' % config['grpcport'])
    stub = pb_grpc.HexliteAnswerSetSolverStub(channel)

    job = pb.SolverJob()
    job.program = 'a :- not b. b :- not a. { c ; d ; e }. :~ a. [1,a] :~ c. [1,c]'
    job.parameters.number_of_answers = 5
    job.parameters.additional_parameters.append(pb.KeyValuePair(
        key='file:script.sh',
        value='echo "hello from the shell";\n'
    ))

    response = stub.solve(job)

    logging.info("expect 4 optimal answers: {b}, {b,e}, {b,d}, {b,d,e})")
    logging.info("response success=%s/%d with %d answersets:", response.description.success, response.description.code, len(response.answers))
    for a in response.answers:
        logging.info("    cost=%s optimal=%s atoms=%s", a.costs, a.is_known_optimal, ' '.join(a.atoms))
    for idx, m in enumerate(response.description.messages):
        logging.info("message %d:", idx + 1)
        logging.info(m)

main()
