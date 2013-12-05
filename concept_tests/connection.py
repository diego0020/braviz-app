__author__ = 'Diego'

from braviz.applications import multiple_variables,mriMultSlicer
import multiprocessing
import time

if __name__ == "__main__":
    pipe_multVars,pipe_slicer=multiprocessing.Pipe()
    mult_vars = multiprocessing.Process(target=multiple_variables.launch_new, args=(pipe_multVars,))
    mult_slicer = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_slicer,))
    mult_vars.start()
    mult_slicer.start()
    while True:
        if mult_vars.is_alive() and mult_slicer.is_alive():
            time.sleep(1)
        else:
            print "all done"
            break

    if mult_vars.is_alive():
        mult_vars.terminate()
    if mult_slicer.is_alive():
        mult_slicer.terminate()

    mult_vars.join()
    mult_slicer.join()


