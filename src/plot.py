# user defined variables
state = 'nc' #input('State: ')
service = 'gas_station'#'gas_station'

from config import *
db, context = cfg_init(state)
logger = logging.getLogger(__name__)

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.style as style

from matplotlib import cm
import datetime

save_to_sf = True
# define the plotting style
plt.style.use(['tableau-colorblind10'])#,'dark_background'])
fig_transparency = False

font_size = 8
dpi = 500
# additional parameters
params = {'axes.labelsize': font_size, # fontsize for x and y labels (was 10)
          'font.size': font_size, # was 10
          'legend.fontsize': font_size * 2/3, # was 10
          'xtick.labelsize': font_size,
          'font.family' : 'Myriad Pro',
          # 'ytick.labelsize': 0,
          'lines.linewidth' : 1,
          'figure.autolayout' : True,
          'figure.figsize': [3,1.5],#[fig_width/2.54,fig_height/2.54]
          'axes.spines.top'    : False,
          'axes.spines.right'  : False,
          'axes.xmargin' : 0
}

font_size = 5
param_ecdf = {'axes.labelsize': font_size, # fontsize for x and y labels (was 10)
          'font.size': font_size, # was 10
          'legend.fontsize': font_size * 2/3, # was 10
          'xtick.labelsize': font_size,
          'figure.figsize': [4/2.54,2.3/2.54],#[fig_width/2.54,fig_height/2.54]
          'lines.linewidth' : 0.5
}

mpl.rcParams.update(params)

def main():
    '''
    plots
    '''
    services = ['supermarket','gas_station']#, 'super_market']
    # import the service operational ids over time
    operating = {}
    for service in services:
        operating[service] = import_operating(service)
        # service_restoration(service)
    # Plot service restoration
    # for michael i want to end at Nov 25
    date_list = list(operating[service].keys())
    # code.interact(local=locals())
    if state == 'fl':
        date_loop = np.linspace(0,1128,10)
        # delete the future dates
        for service in services:
            operating[service] = {t:operating[service][t] for t in date_list[0:1130]}
    else:
        date_loop = np.linspace(0,len(date_list)-1,10)
    # for i in date_loop:
    # code.interact(local=locals())
    i = date_loop[1]#3]#1]
    time_stamp = date_list[int(i)]
    #
    # plot_ecdf(time_stamp, 'both', operating)
    for service in services:
        resilience_curve(service, operating, time_stamp)
        # Plot choropleth
        # plot_ecdf(time_stamp, service, operating)
        # choropleth_city(time_stamp, service, operating, save_to_sf)


def choropleth_city(time_stamp, service, operating, save_to_sf = False):
    '''
    Plot city blocks and destinations
    '''
    # import the data for the census blocks
    if state == 'fl':
        sql = "SELECT block.geoid10, block.geom FROM block, city WHERE ST_Intersects(block.geom, ST_Transform(city.geom, 4269)) AND city.name = 'Panama City'"
    else:
        sql = "SELECT block.geoid10, block.geom FROM block, city WHERE ST_Intersects(block.geom, ST_Transform(city.geom, 4269)) AND city.juris = 'WM'"
    df = gpd.GeoDataFrame.from_postgis(sql, con, geom_col='geom')
    # import the locations of the services
    sql = "SELECT id, dest_type, geom FROM destinations WHERE dest_type = %s;"
    if state == 'fl' and service == 'super_market':
        dests = gpd.GeoDataFrame.from_postgis(sql, con, params = ('super_market_operating',))
    else:
        dests = gpd.GeoDataFrame.from_postgis(sql, con, params = (service,))
    dests.set_index('id', inplace=True)
    dests['Operational'] = False
    # which services are operating
    ids_open = operating[service][time_stamp]
    # code.interact(local=locals())
    dests.loc[ids_open, 'Operational']  = True
    # import the distance to the nearest service for this time
    sql = 'SELECT distance, id_orig FROM {} WHERE time_stamp = %s AND service = %s'.format(context['nearest_db_name'])
    dist = pd.read_sql(sql, con, params = (time_stamp, service,))
    # merge distance into blocks
    df = df.merge(dist, left_on = 'geoid10', right_on = 'id_orig')
    # create the distance bins
    bins = [0,1000,2000,3000,4000,np.inf]
    def bin_mapping(x):
        for idx, bound in enumerate(bins):
            if x < bound:
                return bound
    bin_labels = [idx / (len(bins) - 1.0) for idx in range(len(bins))]
    df['Bin_Lbl'] = df['distance'].apply(bin_mapping)
    # plot
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    # plot blocks
    ch = df.plot(ax=ax, column='Bin_Lbl', cmap='OrRd', alpha=1,vmin=0,vmax=5000)#, legend=True)#, color='white', edgecolor='black')
    # plt.colorbar(ch,{'orientation':'horizontal'})
    ax.autoscale(False)
    # plot destinations
    on = dests[dests['Operational']==True].plot(ax=ax, marker='v', color='cornflowerblue', markersize=15, label = 'open');
    off = dests[dests['Operational']==False].plot(ax=ax, marker='v', color='black', markersize=15, label = 'closed');
    # formatting
    ax.set_axis_off()
    if service == 'gas_station':
        # plt.title('Proximity (m) to open gas station at {}'.format(time_stamp.strftime("%Y-%m-%d %H:%M")))
        # plt.title('Meters to gas station')
        plt.title('{}'.format(time_stamp.strftime("%d-%b-%Y")))
    else:
        # plt.title('Proximity (m) to open super market at {}'.format(time_stamp.strftime("%d-%b-%Y")))
        plt.title('{}'.format(time_stamp.strftime("%d-%b-%Y")))
    # legend
    # import code
    # code.interact(local=locals())
    # lns = ch + on + off
    # labs = [l.get_label() for l in lns]
    # plt.legend(lns, labs, loc='center left')#, bbox_to_anchor=(1, 0.5))
    # ax.get_legend().set_bbox_to_anchor((.12, .4))
    # save shapefiles
    if save_to_sf:
        # add population information
        sql = 'SELECT "H7X001", geoid10 FROM demograph;'
        pop = pd.read_sql(sql, con)
        # merge with the df
        df = df.merge(pop, on = 'geoid10')
        # save shapes
        df.to_file('fig/gif_{}/map_blocks_{}_{}.shp'.format(state,service,time_stamp.strftime("%Y%m%d-%H")))
        dests.Operational = dests.Operational.astype(int)
        dests.to_file('fig/gif_{}/map_dests_{}_{}.shp'.format(state,service,time_stamp.strftime("%Y%m%d-%H")))
    # save fig
    fig_out = 'fig/gif_{}/choropleth_{}_{}.png'.format(state,service,time_stamp.strftime("%Y%m%d-%H"))
    if os.path.isfile(fig_out):
        os.remove(fig_out)
    # plt.savefig('fig/choropleth_{}_{}.pdf'.format(service,time_stamp.strftime("%Y%m%d-%H")), dpi=dpi, format='pdf', transparent=fig_transparency)
    plt.savefig(fig_out, dpi=dpi, format='png', transparent=fig_transparency)
    plt.clf()


def service_restoration(service):
    '''
    plot the number of services as they are restored
    '''
    with open('data/destinations/{}_operating_{}.pk'.format(service,state.upper()), 'rb') as fp:
        outages = pk.load(fp)
    # prepare data
    x = []
    y = []
    for i in outages:
        x.append(i['datetime'])
        y.append(len(i['operational_ids']))
    # plot
    plt.plot(x,y)
    # land fall line
    # plt.axvline(datetime(2018,9,14,7,0),ls='--')
    # plt.text(datetime(2018,9,14,15,0), 500,'landfall')
    # x ticks
    # import code
    # code.interact(local=locals())
    x_dummy = np.linspace(0,len(x)-1,8)
    t_dummy = [x[int(i)].date() for i in x_dummy]
    plt.xticks(t_dummy, t_dummy, rotation=45)
    # labels
    if service == 'gas_station':
        plt.ylabel('Operational gas stations')
    else:
        plt.ylabel('Open super market')
    # save fig
    plt.savefig('fig/restoration_{}_{}.png'.format(service, state), dpi=dpi, format='png', transparent=fig_transparency, bbox_inches='tight')
    plt.clf()


def plot_ecdf(time_stamp, service, operating):
    '''
    plot the ecdf at a certain time
    '''
    mpl.rcParams.update(param_ecdf)
    # plt.figure(figsize=(4/2.54,2.3/2.54))
    for serv in ['super_market','gas_station']:
        # calculate the ecdf data
        pop = calc_ecdf(time_stamp, serv, operating)
        # plot the cdf
        plt.plot(pop.distance/1000, pop.perc, label = 'white')
    # ylabel
    # plt.ylabel('% residents')
    # xlabel
    if service == 'gas_station':
        plt.xlabel('Distance to open facility (km)')
    else:
        plt.xlabel('Distance to open facility (km)')
    plt.xlim([0,12])
    plt.ylim([0,None])
    # plt.title('{}'.format(time_stamp.strftime("%d-%b-%Y")))
    # plt.title(time_stamp, loc='left')
    # plt.legend()

    # savefig
    fig_out = 'fig/gif_{}/cdf_{}_{}.pdf'.format(state,service,time_stamp.strftime("%Y%m%d-%H"))
    if os.path.isfile(fig_out):
        os.remove(fig_out)
    plt.savefig(fig_out, dpi=dpi, format='pdf', transparent=fig_transparency)#, bbox_inches='tight')
    plt.clf()


def resilience_curve(service, operating, time_stamp):
    '''
    Plot the resilience curve
    '''
    # db connection
    con = db['con']
    cursor = con.cursor()
    # timestamp
    time_stamp_line = time_stamp
    # percentiles
    percentiles = np.linspace(0,1,11)[1:-1]
    col_list = ['#ffffcc','#ffeda0','#fed976','#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026']
    # init df
    times = sorted(operating[service].keys())
    df = pd.DataFrame({'time_stamp':times})
    for p in percentiles:
        df['p{0:0.1f}'.format(p)] = None
    df['mean'] = None
    df_names = ['p{0:0.1f}'.format(i) for i in percentiles]
    # loop through time
    for index, row in df.iterrows():
        time_stamp = df.loc[index,'time_stamp']
        pop = calc_ecdf(time_stamp, service, operating)
        # code.interact(local=locals())
        resil_values = weighted_quantile(pop.distance.values, percentiles, sample_weight=pop.H7X001.values, values_sorted=True)
        df.loc[index, 'mean'] = np.average(pop.distance.values, weights = pop.H7X001.values)
        df.loc[index,df_names] = resil_values

    if state == 'fl' and service == 'gas_station':
        df['mean'] = df['mean'].rolling(10).median()
        for i in range(len(percentiles)):
            df[df_names[i]] = df[df_names[i]].rolling(10).median()

    # plot
    # import code
    # code.interact(local=locals())
    for i in range(len(percentiles)-1):
        plt.fill_between(df.time_stamp.values, np.array(df[df_names[i]], dtype = float)/1000, np.floor(np.array(df[df_names[i+1]], dtype = float))/1000, alpha=0.7, color = col_list[i])
    plt.plot(df.time_stamp, df['mean']/1000, label = service, color = 'k')
    plt.plot(df.time_stamp, np.array(df[df_names[0]], dtype = float)/1000, linestyle = '--', color = 'k')
    plt.plot(df.time_stamp, np.array(df[df_names[i+1]], dtype = float)/1000, linestyle = '--', color = 'k')
    plt.axvline(x=time_stamp_line, color = 'k')
    # land fall
    if state == 'fl':
        plt.axvline(datetime.datetime(2018,10,10,12,0),ls='--', color = 'k')
        # plt.text(datetime(2018,10,10,20,0), 500,'landfall')
        plt.xlim([None, datetime.datetime(2018,11,9,12,0)])
        x_len = df.index[df.time_stamp == datetime.datetime(2018,11,9,0,0)].tolist()[0]
        # x_len = len(df.time_stamp)-1
    else:
        plt.axvline(datetime.datetime(2018,9,14,7,0),ls='--', color = 'k', linewidth=0.5)
        # plt.text(datetime(2018,9,11,0,0), 3.5,'Hurricane Florence \n landfall', fontsize=5)
        plt.xlim([None, datetime.datetime(2018,9,29,0,0)])
        x_len = df.index[df.time_stamp == datetime.datetime(2018,9,29,0,0)].tolist()[0]
    # x ticks
    x_dummy = np.linspace(0,x_len,4)
    # code.interact(local=locals())
    x_locs = [df.time_stamp[int(i)].date().strftime("%d-%b-%Y") for i in x_dummy]
    x_locs = [datetime.datetime.strptime(i,"%d-%b-%Y") for i in x_locs]
    x_labels = [df.time_stamp[int(i)].date().strftime("%d-%b") for i in x_dummy]
    # x_labels = [dist_id.time_stamp[int(i)].date().strftime("%d-%b") for i in x_dummy]
    plt.xticks(ticks=x_locs, labels=x_labels, rotation=0)
    # ylabel
    # plt.ylim([0,4])

    if service == 'gas_station':
        # plt.ylabel('Distribution of distance \n to open gas station (m)')
        plt.ylabel('Km to open facility')
    else:
        plt.ylabel('Km to open facility')

        # plt.yticks([2,5,8])
    plt.ylim([0,None])
    plt.gca().invert_yaxis()
    # legend
    # plt.legend(loc='lower right')
    # savefig
    # plt.show()
    fig_out = 'fig/gif_{}/resilience_{}_{}.pdf'.format(state,service,time_stamp_line.strftime("%Y%m%d-%H"))
    if os.path.isfile(fig_out):
        os.remove(fig_out)
    plt.savefig(fig_out, dpi=dpi, format='pdf')#, bbox_inches='tight', transparent=fig_transparency)
    # plt.show()
    plt.clf()


def calc_ecdf(time_stamp, service, operating):
    '''
    calculate the ecdf at a certain time
    '''
    # db connection
    con = db['con']
    # import the distance to the nearest service for this time
    sql = "SELECT distance, id_orig FROM {} WHERE time_stamp = %s AND service = %s".format(context['nearest_db_name'])
    dist = pd.read_sql(sql, con, params = (time_stamp, service,))
    # import number of people
    sql = 'SELECT "H7X001", "H7X002", geoid10 FROM demograph;'
    pop = pd.read_sql(sql, con)
    # merge population into blocks
    pop = pop.merge(dist, left_on = 'geoid10', right_on = 'id_orig')
    pop['white'] = pop.H7X002
    pop['nonwhite'] = pop.H7X001 - pop.H7X002
    # total population
    pop_total = pop.H7X001.sum()
    # pop_nonwhite
    pop_nonwhite_total = pop.nonwhite.sum()
    pop_white_total = pop.white.sum()
    # sort df by distance (ascending)
    pop = pop.sort_values('distance')
    # column for percent of residents
    pop['perc'] = pop.H7X001.cumsum()/pop_total*100
    pop['nonwhite_perc'] = pop.nonwhite.cumsum()/pop_nonwhite_total*100
    pop['white_perc'] = pop.white.cumsum()/pop_white_total*100
    # return df
    return(pop)

def import_operating(service_name):
    '''
    import the station and store outages and prepare the dict
    '''
    # import data
    if state=='fl':
        in_name = 'data/pan/destination/{}.pk'
    else:
        in_name = 'data/wil/destination/{}.pk'
    with open(in_name.format(service_name), 'rb') as fp:
        operating = pk.load(fp)
    # convert to dict for faster querying
    dict = {d['datetime']:d['operational_ids'] for d in operating}
    return(dict)


def weighted_quantile(values, quantiles, sample_weight=None, values_sorted=False, old_style=False):
    # https://stackoverflow.com/questions/21844024/weighted-percentile-using-numpy/29677616#29677616
    """ Very close to numpy.percentile, but supports weights.
    NOTE: quantiles should be in [0, 1]!
    :param values: numpy.array with data
    :param quantiles: array-like with many quantiles needed
    :param sample_weight: array-like of the same length as `array`
    :param values_sorted: bool, if True, then will avoid sorting of initial array
    :param old_style: if True, will correct output to be consistent with numpy.percentile.
    :return: numpy.array with computed quantiles.
    """
    values = np.array(values)
    quantiles = np.array(quantiles)
    if sample_weight is None:
        sample_weight = np.ones(len(values))
    sample_weight = np.array(sample_weight)
    assert np.all(quantiles >= 0) and np.all(quantiles <= 1), 'quantiles should be in [0, 1]'
    #
    if not values_sorted:
        sorter = np.argsort(values)
        values = values[sorter]
        sample_weight = sample_weight[sorter]
    #
    weighted_quantiles = np.cumsum(sample_weight) - 0.5 * sample_weight
    if old_style:
        # To be convenient with np.percentile
        weighted_quantiles -= weighted_quantiles[0]
        weighted_quantiles /= weighted_quantiles[-1]
    else:
        weighted_quantiles /= np.sum(sample_weight)
    return np.interp(quantiles, weighted_quantiles, values)

if __name__ == "__main__":
    main()
