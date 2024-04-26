import pandas as pd

def calculate_aggregations(base_df, group_columns):
    grouped_data = base_df.groupby(group_columns).agg({'kendra_id': list}).reset_index()
    grouped_data['count'] = grouped_data['kendra_id'].apply(len)
    total_count_data = base_df.groupby(group_columns[:-1]).size().reset_index(name='total_count')
    proportion_data = pd.merge(grouped_data, total_count_data, on=group_columns[:-1])
    proportion_data['proportion'] = proportion_data['count'] / proportion_data['total_count']
    proportion_data['proportion'] = proportion_data['proportion'].apply(lambda x: round(x, 3))

    # Aggregating kendra_id by status, treating date as a free variable
    union_data = base_df.groupby('status')['kendra_id'].apply(lambda x: set(x)).reset_index()
    union_data.rename(columns={'kendra_id': 'kendra_id_union'}, inplace=True)
    union_data['total_unique'] = union_data['kendra_id_union'].apply(len)
    union_data.drop('kendra_id_union', axis=1, inplace=True)

    proportion_data = pd.merge(proportion_data, union_data, on='status', how='left')

    return proportion_data

def get_manager_stats(df, case='All'):
    total_drivers = df.groupby('manager')['driver_id'].count().reset_index(name='total_drivers')

    columns_order = [
            'manager', 'total_drivers', 'matched_drivers', 'unmatched_drivers', 'matched_percentage',
            'avg_distance', 'median_distance', 'min_distance', 'max_distance'
        ]

    if case == 'All':
        manager_stats = df.groupby('manager').agg(
            total_drivers=('driver_id', 'count'),
            matched_drivers=('is_matched', 'sum'),
            unmatched_drivers=('is_matched', lambda x: (x == 0).sum()),
            avg_distance=('distance', lambda x: round(x.mean() / 1000, 2)),
            median_distance=('distance', lambda x: round(x.median() / 1000, 2)),
            min_distance=('distance', lambda x: round(x.min() / 1000, 2)),
            max_distance=('distance', lambda x: round(x.max() / 1000, 2))
        ).reset_index()

        manager_stats['matched_percentage'] = round(manager_stats['matched_drivers'] / manager_stats['total_drivers'] * 100, 2)
        
        manager_stats = manager_stats[columns_order]
        manager_stats['exchange_location'] = "General"
    else:
        manager_stats = df[df['exchange_location'] == case].groupby('manager').agg(
            count=('exchange_location', 'count'),
            matched_drivers=('is_matched', 'sum'),
            unmatched_drivers=('is_matched', lambda x: (x == 0).sum()),
            avg_distance=('distance', lambda x: round(x.mean() / 1000, 2)),
            median_distance=('distance', lambda x: round(x.median() / 1000, 2)),
            min_distance=('distance', lambda x: round(x.min() / 1000, 2)),
            max_distance=('distance', lambda x: round(x.max() / 1000, 2))
        ).reset_index()

        manager_stats['matched_percentage'] = round(manager_stats['matched_drivers'] / manager_stats['count'] * 100, 2)
        manager_stats = manager_stats.merge(total_drivers, on='manager', how='left')
        manager_stats['percentage'] = round(manager_stats['count'] / manager_stats['total_drivers'] * 100, 2)

        manager_stats = manager_stats.drop('total_drivers', axis=1)
        manager_stats = manager_stats.rename(columns={'count': 'total_drivers'})
        manager_stats = manager_stats[columns_order]
        manager_stats['exchange_location'] = case
    
    return manager_stats

def calculate_status_periods(base_df):
    # Ensure 'date' is in datetime format
    base_df['date'] = pd.to_datetime(base_df['date'])

    # Sort the DataFrame by 'plate' and 'date' to ensure correct order
    base_df.sort_values(by=['plate', 'date'], inplace=True)

    # Calculate the difference in days between each row's date and the previous row's date for each plate
    base_df['date_diff'] = base_df.groupby('plate')['date'].diff().dt.days

    # Flag rows where the status changes or the date difference is more than 1 day
    base_df['status_change'] = (base_df['status'] != base_df['status'].shift()) | (base_df['date_diff'] > 1)

    # Cumulatively sum the flags to create unique groups for continuous periods
    base_df['group'] = base_df.groupby('plate')['status_change'].cumsum()

    # Group by 'plate', 'status', and 'group' to calculate the length of each continuous period
    continuous_periods = base_df.groupby(['plate', 'status', 'group']).size().reset_index(name='length')

    # Find the longest continuous period for each plate
    longest_continuous_periods = continuous_periods.loc[continuous_periods.groupby(['plate'])['length'].idxmax()]

    # Calculate the total period for each status of a plate, regardless of continuity
    total_periods = base_df.groupby(['plate', 'status']).size().reset_index(name='total_length')

    # Find the status with the longest total period for each plate
    longest_total_periods = total_periods.loc[total_periods.groupby(['plate'])['total_length'].idxmax()]

    # Merge the longest continuous and total periods into a single DataFrame
    merged_periods = pd.merge(longest_continuous_periods, longest_total_periods, on='plate', suffixes=('_cont', '_total'))

    # Select and rename columns
    merged_periods = merged_periods[['plate', 'status_cont', 'length', 'status_total', 'total_length']]
    merged_periods.rename(columns={'status_cont': 'longest_continued_status', 'length': 'longest_continued_days', 'status_total': 'greatest_total_status', 'total_length': 'greatest_total_days'}, inplace=True)

    return merged_periods


def filter_and_format(base_df, date, status):
    filtered_df = base_df[(pd.to_datetime(base_df['date']).dt.date == date) & (base_df['status'] == status)].copy()
    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
    filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d')
    filtered_df.drop(columns=['kendra_id', 'date', 'status'], inplace=True)
    return filtered_df

def sanity_check(expected_count, actual_count):
    """
    Performs a sanity check comparing expected and actual counts.
    Returns a message if there's a mismatch, otherwise None.
    """
    if expected_count != actual_count:
        return f"Something is rotten in the state of Denmark: Expected {expected_count} rows, but found {actual_count}. Please contact Carlos at trebbau@auro-group.com"
    return None

def calculate_block_holes(vehicle_shifts):
    block_holes = []
    for date, group in vehicle_shifts.groupby('date'):
        # Define blocks for the current group/date only
        group['block_0'] = (group[['manana', 'tarde', 'turno_completo', 'tp_v_d', 'tp_l_v', 'l_j', 'l_j_40h']].sum(axis=1) == 0)
        group['block_1'] = (group['turno_completo'] == 1)
        group['block_2'] = (group['tarde'] == 1)
        group['block_3'] = ((group['l_j'] + group['l_j_40h'] + group['manana'] + group['tp_l_v'] + group['tp_v_d']) >= 1) & (group['tarde'] == 0) & (group['turno_completo'] == 0)

        # Define holes in each block for the current group/date
        group['hole_block_0'] = group['block_0']
        group['hole_block_1'] = False
        group['hole_block_2'] = (
            (group['block_2'] == 1) &
            (group['manana'] == 0) &
            (group['number_of_drivers'] < 2))
        group['hole_block_3'] = (
            (group['block_3'] == 1) &
            (group['number_of_drivers'] < 3))

        # Combine the holes from all blocks for the current group/date
        group['hole'] = (
            group['hole_block_0'] |
            group['hole_block_1'] |
            group['hole_block_2'] |
            group['hole_block_3'])

        # Init hole counts for the current group/date
        holes = group[group['hole'] == True]
        hole_counts = pd.DataFrame(columns=['plate', 'manager', 'center', 'manana', 'tarde', 'l_j_40h', 'tp_v_d'])

        grouped_holes_df = holes.groupby(['plate', 'manager', 'center'])
        for (plate, manager, center), subgroup in grouped_holes_df:
            hole_counts.loc[len(hole_counts)] = [plate, manager, center, 0, 0, 0, 0]
        
            for _, row in subgroup.iterrows():
                if row['block_0'] == True:
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'manana'] += 1
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'l_j_40h'] += 1
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'tp_v_d'] += 1
                elif row['block_1'] == True:
                    pass
                elif row['block_2'] == True:
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'manana'] += 1
                elif row['block_3'] == True:
                    if row['manana'] == 0 and row['tp_l_v'] == 0:
                        hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'manana'] += 1
                    if row['l_j'] == 0 and row['l_j_40h'] == 0:
                        hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'l_j_40h'] += 1
                    if row['tp_v_d'] == 0:
                        hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'tp_v_d'] += 1

        total_by_manager_df = hole_counts.groupby(['manager', 'center']).sum().reset_index()
        total_by_manager_df['total'] = total_by_manager_df[['manana', 'tarde', 'l_j_40h', 'tp_v_d']].sum(axis=1)
        total_by_manager_df.drop(columns=['plate'], inplace=True)

        consolidated_total_df = pd.DataFrame({
            'manager': ['total'],
            'center': [''],
            'manana': [total_by_manager_df['manana'].sum()],
            'tarde': [total_by_manager_df['tarde'].sum()],
            'l_j_40h': [total_by_manager_df['l_j_40h'].sum()],
            'tp_v_d': [total_by_manager_df['tp_v_d'].sum()],
            'total': [total_by_manager_df['total'].sum()]
        })

        total_by_manager_df = pd.concat([total_by_manager_df, consolidated_total_df], ignore_index=True)
        total_by_manager_df['date'] = date
        block_holes.append(total_by_manager_df)
    
    block_holes_df = pd.concat(block_holes, ignore_index=True)
    return block_holes_df





