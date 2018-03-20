'''
Created on March 20, 2018

@author: Alejandro Molina
'''

from collections import deque

from enum import Enum
import numpy as np

from src.spn.structure.Base import *


class Operation(Enum):
    CREATE_LEAF = 1
    SPLIT_COLUMNS = 2
    SPLIT_ROWS = 3
    REMOVE_UNINFORMATIVE_FEATURES = 4

def next_operation(data, no_clusters=False, no_independencies=False, is_first=False, cluster_first=True, cluster_univariate=False, min_instances_slice=100):

    minimalFeatures = data.shape[1] == 1
    minimalInstances = data.shape[0] <= min_instances_slice

    if minimalFeatures:
        if minimalInstances or no_clusters:
            return Operation.CREATE_LEAF
        else:
            if cluster_univariate:
                return Operation.SPLIT_ROWS
            else:
                return Operation.CREATE_LEAF

    ncols_zero_variance = np.sum(np.var(data, 0) == 0)
    if ncols_zero_variance > 1:
        if ncols_zero_variance == data.shape[1]:
            return Operation.CREATE_LEAF
        else:
            return Operation.REMOVE_UNINFORMATIVE_FEATURES

    if minimalInstances or (no_clusters and no_independencies):
        return Operation.CREATE_LEAF

    if no_independencies:
        return Operation.SPLIT_ROWS

    if no_clusters:
        return Operation.SPLIT_COLUMNS

    if is_first:
        return Operation.SPLIT_ROWS if cluster_first else Operation.SPLIT_COLUMNS

    return Operation.SPLIT_COLUMNS




def LearnStructure(dataset, ds_context, next_operation, split_rows, split_cols, create_leaf):

    root = Product()
    root.children.append(None)

    tasks = deque()
    tasks.append((dataset, root, 0, False, False))

    while tasks:

        local_data, parent, children_pos, scope, no_clusters, no_independencies = tasks.popleft()

        operation = next_operation(local_data, no_clusters=no_clusters, no_independencies=no_independencies,
                                   is_first=(parent is root))


        if operation == Operation.REMOVE_UNINFORMATIVE_FEATURES:
            variances = np.var(local_data, axis=0)

            node = Product()
            node.scope.extend(scope)
            parent.children[children_pos] = node

            cols = []
            for col in range(local_data.shape[1]):
                if variances[col] == 0:
                    node.children.append(None)
                    tasks.append((local_data[:, col], node, len(node.children)-1, [col], True, True))
                else:
                    cols.append(col)

            node.children.append(None)
            tasks.append((local_data[:, cols], node, len(node.children) - 1, cols, False, False))

            continue

        elif operation == Operation.SPLIT_ROWS:

            data_slices = split_rows(local_data, ds_context, scope)

            if len(data_slices) == 1:
                tasks.append((local_data, parent, children_pos, scope, True, False))
                continue

            node = Sum()
            node.scope.extend(scope)
            parent.children[children_pos] = node

            for data_slice in data_slices:
                node.children.append(None)
                node.weights.append(data_slice.shape[0]/local_data.shape[0])
                tasks.append((data_slice, node, len(node.children) - 1, scope, False, False))

            continue

        elif operation == Operation.SPLIT_COLUMNS:
            data_slices = split_cols(local_data, ds_context, scope)

            if len(data_slices) == 1:
                tasks.append((local_data, parent, children_pos, scope, False, True))
                continue

            node = Product()
            node.scope.extend(scope)
            parent.children[children_pos] = node

            for data_slice, scope_slice in data_slices:
                node.children.append(None)
                tasks.append((data_slice, node, len(node.children) - 1, scope_slice, False, False))
            continue

        elif operation == Operation.CREATE_LEAF:
            node = create_leaf(local_data, ds_context, scope)
            node.scope.extend(scope)
            parent.children[children_pos] = node

        else:
            raise Exception('Invalid operation: ' + operation)

    return root.children[0]

def Prune(node):

    if not isinstance(node, Sum) and not isinstance(node, Product):
        return node


    while True:
        pruneNeeded = any(map(lambda c: isinstance(c, type(node)), node.children))

        if not pruneNeeded:
            return node

        newNode = node.__class__()
        newNode.scope.extend(node.scope)

        newChildren = []
        newWeights = []
        for i, c in enumerate(node.children):
            if type(c) != type(newNode):
                newChildren.append(c)
                continue

            for j, gc in enumerate(c.children):
                newChildren.append(gc)
                if type(c) == Sum:
                    newWeights.append(node.weights[i] * c.weights[j])

        newNode.children.extend(newChildren)

        if type(newNode) == Sum:
            newNode.weights.extend(newWeights)

        node = newNode

    return node
