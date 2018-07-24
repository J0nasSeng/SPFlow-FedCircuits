import numpy as np
import os; path = os.path.dirname(__file__)
from tempfile import mkdtemp
from networkx.algorithms.components.connected import connected_components
from networkx.convert_matrix import from_numpy_matrix
from rpy2 import robjects
from rpy2.robjects import numpy2ri
from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage


with open("RCoT.R", "r") as mixfile:
   code = ''.join(mixfile.readlines())
   CoTest = SignatureTranslatedAnonymousPackage(code, "RCoT")


data_file = path.join(mkdtemp(), 'data_file.dat')
data_cond_file = path.join(mkdtemp(), 'data_cond_file.dat')



def getCIGroups(dataIn, alpha=0.0001, families=None):
    """
    This function take tuple (output, conditional) as input and returns independent groups
    alpha is the cutoff parameter for connected components
    BE CAREFUL WITH SPARSE DATA!
    """
    data, data_cond = dataIn

    DATA = np.memmap(data_file, dtype=data.dtype, mode='w+', shape=data.shape)
    DATA[:] = data[:]
    DATA.flush()

    DATA_COND = np.memmap(data_cond_file, dtype=data_cond.dtype, mode='w+', shape=data_cond.shape)
    DATA_COND[:] = data_cond[:]
    DATA_COND.flush()

    num_X = data.shape[1] #len(data[0])
    num_Y = data_cond.shape[1] #len(data_cond[0])
    p_value_matrix = np.zeros((num_X, num_X))

    index_matrix = [(x, y, data.dtype, data.shape, data_cond.shape) for x in range(num_X) for y in range(num_X)]
    index_matrix = [s for s in index_matrix if s[0]!=s[1]]

    with mp.Pool() as pool:
        pvals = pool.starmap(computePvals, index_matrix) #index_matrix)

    pvals_container = np.zeros((num_X,num_X))
    d = np.diag_indices_from(pvals_container)
    pvals_container[d] = 0

    pvals = np.array(pvals).ravel()
    for i in range(len(pvals)):
        x, y, _, _, _ = index_matrix[i]
        pvals_container[x,y] = pvals[i]

    pvals = pvals_container

    for i, j in zip(*np.tril_indices(pvals.shape[1])):
        pvals[i, j] = pvals[j, i] = min(pvals[i, j], pvals[j, i])

    pvals[pvals > alpha] = 0


    result = np.zeros(data.shape[1])
    for i, c in enumerate(connected_components(from_numpy_matrix(pvals))):
        result[list(c)] = i + 1

    print('result', result)
    return result


def computePvals(x, y, data_type, data_shape, data_cond_shape):

    DATA = np.memmap(data_file, dtype=data_type, mode='r', shape=data_shape)
    DATA_COND = np.memmap(data_cond_file, dtype=data_type, mode='r', shape=data_cond_shape)

    num_inst = np.shape(DATA[:,x])[0]
    X_1 = np.asarray(DATA[:,x]).reshape(num_inst, 1)
    X_2 = np.asarray(DATA[:,y]).reshape(num_inst, 1)
    Y = np.asarray(DATA_COND)
    try:
        result = RcoT(X_1, X_2, Y)
        result = result[0][0]
    except Exception as e:
        print(e)
        np.savetxt('X', X_1, fmt='%d')
        np.savetxt('Y', X_2, fmt='%d')
        np.savetxt('Z', Y, fmt='%d')
        raise e

    return result


def RcoT(x,y,z):
    numpy2ri.activate()
    try:
        df_x = robjects.r["as.data.frame"](x)
        df_y = robjects.r["as.data.frame"](y)
        df_z = robjects.r["as.data.frame"](z)
        result = CoTest.RCoT(df_x,df_y,df_z)
        result = np.asarray(result)
    except Exception as e:
        print(e)
        print(z)
        print(z.shape)
        np.savetxt('X', x, fmt='%d')
        np.savetxt('Y', y, fmt='%d')
        np.savetxt('Z', z, fmt='%d')
        raise e

    return result
