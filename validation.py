import pandas as pd
import seaborn as sns
from scipy.stats import ks_2samp
import json
import sys
import argparse
from statistics import mean
import time
from numba import jit
#setting the expected parameters
def createParser ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-source', '--source_type_cell', type=str)
    parser.add_argument('-target', '--target_type_cell', type=str)
    #parser.add_argument('-signatures', '--path_to_file_with_signatures',default = 'DATA/CD_signatures_binary_42809.gmt', type = argparse.FileType())
    parser.add_argument('-dir_results', '--path_to_dir_save_results', default = 'DATA', type = str)
    parser.add_argument('-cd_signature_metadata', '--path_to_file_with_cd_signature_metadata',
                        default = 'DATA/CD_signature_metadata.csv', type = str)
    parser.add_argument('-drugs_metadata', '--path_to_file_with_drugs_metadata',
                        default='DATA/Drugs_metadata.csv', type=str)
    parser.add_argument('-intersect_cfm_l1000fwd', '--path_to_file_with_intersect_cfm_l1000fwd',
                        default='DATA/table_of_cell_conversion_and_chemicals_1.csv', type=str)

    return parser
#@jit
def modernization(data_intersect_CFM_L1000FWD, data_Drugs_metadata, data_CD_signature_metadata):
    #для малых молекул из L1000FWD по cid найдем pert_id
    data_intersect_CFM_L1000FWD['pert_id of chemicals in L1000FWD'] = str()
    for i in range(data_intersect_CFM_L1000FWD.shape[0]):
        if data_intersect_CFM_L1000FWD.iloc[i, 8] != 'not molecules':
            for cid in data_intersect_CFM_L1000FWD.iloc[i, 8].split(';'):
                if data_intersect_CFM_L1000FWD.iloc[i, 9] == str():
                    data_intersect_CFM_L1000FWD.iloc[i, 9] = ';'.join(list(data_Drugs_metadata[data_Drugs_metadata['pubchem_cid'] == cid].index))
                else:
                    data_intersect_CFM_L1000FWD.iloc[i, 9] = data_intersect_CFM_L1000FWD.iloc[i, 9] + ';' +  ';'.join(list(data_Drugs_metadata[data_Drugs_metadata['pubchem_cid'] == cid].index))
    #для малых молекул из L1000FWD по pert_id найдем sign_id
    data_intersect_CFM_L1000FWD['sign_id'] = str()
    for i in range(data_intersect_CFM_L1000FWD.shape[0]):
        if data_intersect_CFM_L1000FWD.iloc[i, 9] != str():
            for pert_id in data_intersect_CFM_L1000FWD.iloc[i, 9].split(';'):
                if data_intersect_CFM_L1000FWD.iloc[i, 10] == str():
                    data_intersect_CFM_L1000FWD.iloc[i, 10] = ';'.join(list(data_CD_signature_metadata[data_CD_signature_metadata['pert_id'] == pert_id].index))
                else:
                    data_intersect_CFM_L1000FWD.iloc[i, 10] = data_intersect_CFM_L1000FWD.iloc[i, 10] + ';' + ';'.join(list(data_CD_signature_metadata[data_CD_signature_metadata['pert_id'] == pert_id].index))
    return data_intersect_CFM_L1000FWD

#@jit
def filter(str_source_type_cell, str_target_type_cell, data_intersect_CFM_L1000FWD):
    data_intersect_CFM_L1000FWD = data_intersect_CFM_L1000FWD[(data_intersect_CFM_L1000FWD['Source Cell Type'] == str_source_type_cell)
                                            & (data_intersect_CFM_L1000FWD['Target Cell Type'] == str_target_type_cell)]
    data_intersect_CFM_L1000FWD = data_intersect_CFM_L1000FWD[data_intersect_CFM_L1000FWD['cid of chemicals in L1000FWD'] !=
                                                              'not molecules']
    return data_intersect_CFM_L1000FWD

#@jit
def select_sign_id(data_intersect_CFM_L1000FWD, n):
    list_synergy_pair = []
    for i in range(data_intersect_CFM_L1000FWD.shape[0]):
        list_sign = data_intersect_CFM_L1000FWD.iloc[i, 10].strip().split(';')
        for i in range(len(list_sign)-1):
            for j in range(i+1, len(list_sign)):
                if not ((list_sign[i], list_sign[j]) in list_synergy_pair) and (not ((list_sign[j], list_sign[i]) in list_synergy_pair)):
                    list_synergy_pair.append((list_sign[i], list_sign[j]))

    list_not_synergy_pair = []
    for i in range(data_intersect_CFM_L1000FWD.shape[0] - 1):
        for j in range(i+1, data_intersect_CFM_L1000FWD.shape[0]):
            for sign_id_1 in data_intersect_CFM_L1000FWD.iloc[i, 10].split(';'):
                for sign_id_2 in data_intersect_CFM_L1000FWD.iloc[j, 10].split(';'):
                    if sign_id_1 != sign_id_2 :
                        if (not ((sign_id_1, sign_id_2) in list_not_synergy_pair)) and (not ((sign_id_2, sign_id_1) in list_not_synergy_pair)) and (not((sign_id_1, sign_id_2) in list_synergy_pair)) and (not((sign_id_2, sign_id_1) in list_synergy_pair)):
                            list_not_synergy_pair.append((sign_id_1, sign_id_2))
    list_sign_id = []
    for i in range(n):
        list_sign_id = list_sign_id + data_intersect_CFM_L1000FWD.iloc[i, 10].split(';')
    list_sign_id = list(set(list_sign_id))
    return (list_synergy_pair, list_not_synergy_pair, list_sign_id)
#@jit
def split_by_synergy(df_cosine_dist_matrix, list_synergy_pair, list_not_synergy_pair):
    list_cos_dist_synergy_pair = []
    for pair in list_synergy_pair:
        if (pair[0] in list(df_cosine_dist_matrix.index)) and (pair[1] in list(df_cosine_dist_matrix.index)):
            if list(df_cosine_dist_matrix.index).index(pair[0]) < list(df_cosine_dist_matrix.index).index(pair[1]):
                list_cos_dist_synergy_pair.append(df_cosine_dist_matrix.loc[pair[0], pair[1]])
            else:
                list_cos_dist_synergy_pair.append(df_cosine_dist_matrix.loc[pair[1], pair[0]])

    list_cos_dist_not_synergy_pair = []
    q = 0
    for pair in list_not_synergy_pair:
        q += 1
        print(q)
        if (pair[0] in list(df_cosine_dist_matrix.index)) and (pair[1] in list(df_cosine_dist_matrix.index)):
            if list(df_cosine_dist_matrix.index).index(pair[0]) < list(df_cosine_dist_matrix.index).index(pair[1]):
                list_cos_dist_not_synergy_pair.append(df_cosine_dist_matrix.loc[pair[0], pair[1]])
            else:
                list_cos_dist_not_synergy_pair.append(df_cosine_dist_matrix.loc[pair[1], pair[0]])
    return (list_cos_dist_synergy_pair, list_cos_dist_not_synergy_pair)

def draw(list_cos_dist_synergy_pair, list_cos_dist_not_synergy_pair, path_to_figure):
    snsplot = sns.distplot(list_cos_dist_synergy_pair, color = 'green', label = 'synergy')
    snsplot = sns.distplot(list_cos_dist_not_synergy_pair, color = 'b', label = 'not synergy')
    snsplot.legend()
    snsplot.set_xlabel('score')
    fig = snsplot.get_figure()
    fig.savefig(path_to_figure)

def number_sign_in_protocol(data_intersect_CFM_L1000FWD):
    number_sign = []
    for i in range(data_intersect_CFM_L1000FWD.shape[0]):
        number_sign.append(len(data_intersect_CFM_L1000FWD.iloc[i, 10].split(';')))
    return number_sign
#@jit
def split_signatures(str_source_type_cell, str_target_type_cell, data_intersect_CFM_L1000FWD, data_Drugs_metadata, data_CD_signature_metadata):
    data = modernization(data_intersect_CFM_L1000FWD, data_Drugs_metadata, data_CD_signature_metadata)
    data = filter(str_source_type_cell, str_target_type_cell, data)
    print(number_sign_in_protocol(data))
    syn, not_syn, all_s = select_sign_id(data, len(number_sign_in_protocol(data)))
    return (syn, not_syn, all_s)
#@jit
def statistic_analys_results(set_one, set_two, name_set_one, name_set_two, path_to_results):
    print(len(set_one), len(set_two))
    if len(set_one) > len(set_two) :
        set_big = set_one
        set_small = set_two
    else:
        set_big = set_two
        set_small = set_one
    p_value_list = []
    stat_list = []
    for i in range(len(set_big) // len(set_small) + 1):
        set_big_split = set_big[i * len(set_small): (i + 1) * len(set_small)]
        if len(set_big_split) != len(set_small):
            set_big_split = set_big_split + set_big[0: (len(set_small) - len(set_big_split))]
        (stat, p_value) = ks_2samp(set_big_split, set_small)
        p_value_list.append(p_value)
        print(i, p_value)
        print(len(set_big_split), len(set_small))
        stat_list.append(stat)
    average_p_value = mean(p_value_list)
    average_stat = mean(stat_list)
    dict_statistics= {}
    dict_statistics['average statistic'] = average_stat
    dict_statistics['average pvalue'] = average_p_value
    dict_statistics['statistic values'] = stat_list
    dict_statistics['pvalue values'] = p_value_list
    dict_statistics['mean ' + name_set_one] = mean(set_one)
    dict_statistics['mean ' + name_set_two] = mean(set_two)
    dict_statistics['difference of averagу'] = mean(set_two) - mean(set_one)

    with open(path_to_results,"w") as write_file:
        json.dump(dict_statistics, write_file)
    return dict_statistics

if __name__ == '__main__':
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])
    print(' '.join(namespace.target_type_cell.split('_')))
    data_CD_signature_metadata = pd.read_csv(namespace.path_to_file_with_cd_signature_metadata, index_col=0)
    data_Drugs_metadata = pd.read_csv(namespace.path_to_file_with_drugs_metadata, index_col=0)
    data_intersect_CFM_L1000FWD = pd.read_csv(namespace.path_to_file_with_intersect_cfm_l1000fwd, index_col=0)

    syn, not_syn, all_s = split_signatures(namespace.source_type_cell, ' '.join(namespace.target_type_cell.split('_')), data_intersect_CFM_L1000FWD, data_Drugs_metadata,
                     data_CD_signature_metadata)
    print(len(syn), len(not_syn), len(all_s))
    print(len(set(syn)), len(set(not_syn)), len(set(all_s)))
    with open(namespace.path_to_dir_save_results + '/' + namespace.source_type_cell + '_' + namespace.target_type_cell + '/' + 'list_signatures' + namespace.source_type_cell + '_' + namespace.target_type_cell + '.txt', "w") as file:
        file.write('\n'.join(all_s))

    df_cosine_dist_matrix = pd.read_csv(namespace.path_to_dir_save_results + '/' + namespace.source_type_cell + '_' + namespace.target_type_cell + '/' +
    'cosine_dist_matrix' + '_' + namespace.source_type_cell + '_' + namespace.target_type_cell + '.csv', index_col=0)
    syn_split, not_syn_split = split_by_synergy(df_cosine_dist_matrix, syn, not_syn)
    print(len(syn_split), len(not_syn_split))
    start = time.time()
    d = statistic_analys_results(syn_split, not_syn_split, "synergy", 'not synergy')
    print(time.time() - start)
    print(d)