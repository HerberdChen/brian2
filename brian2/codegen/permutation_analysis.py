'''
Module for analysing synaptic pre and post code for synapse order independence.
'''
from brian2.utils.stringtools import get_identifiers

__all__ = ['OrderDependenceError', 'check_for_order_independence']


class OrderDependenceError(Exception):
    pass


def check_for_order_independence(statements, variables, indices):
    '''
    Check that the sequence of statements doesn't depend on the order in which the indices are iterated through.
    '''
    # Main index variables are those whose index corresponds to the main index being iterated through. By
    # assumption/definition, these indices are unique, and any order-dependence cannot come from their values,
    # only from the values of the derived indices. In the most common case of Synapses, the main index would be
    # the synapse index, and the derived indices would be pre and postsynaptic indices (which can be repeated).
    main_index_variables = set([v for v in variables
                                if (indices[v] in ('_idx', '0')
                                    or getattr(variables[indices[v]],
                                               'unique',
                                               False))])
    different_index_variables = set(variables.keys()) - main_index_variables
    all_variables = variables.keys()
    # At the start, we assume all the different/derived index variables are permutation independent and we continue
    # to scan through the list of statements checking whether or not permutation-dependence has been introduced
    # until the permutation_independent set has stopped changing.
    permutation_independent = list(different_index_variables)
    permutation_dependent_aux_vars = set()
    changed_permutation_independent = True
    for statement in statements:
        if statement.op==':=' and statement.var not in all_variables:
            main_index_variables.add(statement.var)
            all_variables.append(statement.var)
    #index_dependence = dict((k, set([indices[k]])) for k in all_variables)
    while changed_permutation_independent:
        changed_permutation_independent = False
        for statement in statements:
            vars_in_expr = get_identifiers(statement.expr).intersection(all_variables)
            # any time a statement involves a LHS and RHS which only depend on itself, this doesn't change anything
            if set([statement.var])==vars_in_expr:
                continue
            #indices_in_expr = set([indices[k] for k in vars_in_expr])
            nonsyn_vars_in_expr = vars_in_expr.intersection(different_index_variables)
            permdep = any(var not in permutation_independent for var in  nonsyn_vars_in_expr)
            permdep = permdep or any(var in permutation_dependent_aux_vars for var in vars_in_expr)
            if statement.op == ':=': # auxiliary variable created
                if permdep:
                    permutation_dependent_aux_vars.add(statement.var)
                    changed_permutation_independent = True
                continue
            elif statement.var in main_index_variables:
                if permdep:
                    raise OrderDependenceError()
            elif statement.var in different_index_variables:
                if statement.op in ('+=', '*=', '-=', '/='):
                    if permdep:
                        raise OrderDependenceError()
                    if statement.var in permutation_independent:
                        permutation_independent.remove(statement.var)
                        changed_permutation_independent = True
                elif statement.op == '=':
                    otheridx = [v for v in variables
                                if indices[v] not in (indices[statement.var],
                                                      '_idx', '0')]
                    if any(var in otheridx for var in vars_in_expr):
                        raise OrderDependenceError()
                    if permdep:
                        raise OrderDependenceError()
                    if any(var in main_index_variables for var in vars_in_expr):
                        raise OrderDependenceError()
                else:
                    raise OrderDependenceError()
            else:
                raise AssertionError('Should never get here...')


if __name__=='__main__':
    from brian2.codegen.translation import make_statements
    from brian2.core.variables import ArrayVariable
    from brian2 import device
    from numpy import float64
    code = '''
    w_syn = v_pre
    v_pre += 1
    '''
    indices = {'w_syn': '_idx',
               'u_pre': 'presynaptic_idx',
               'v_pre': 'presynaptic_idx',
               'x_post': 'postsynaptic_idx',
               'y_post': 'postsynaptic_idx'}
    variables = dict()
    for var in indices:
        variables[var] = ArrayVariable(var, 1, None, 10, device)
    scalar_statements, vector_statements = make_statements(code, variables, float64)
    check_for_order_independence(vector_statements, variables, indices)
