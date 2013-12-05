__author__ = 'Diego'

from braviz.applications import multiple_variables
import multiprocessing

if __name__ == "__main__":
    mult_vars=multiprocessing.Process(target=multiple_variables.launch_new)
    pipe_a,pipe_b=multiprocessing.Pipe()
    mult_vars.start()
    while True:
        break


    mult_vars.join()


