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
    # Group by manager and calculate total_drivers for all cases
    total_drivers = df.groupby('manager')['driver_id'].count().reset_index(name='total_drivers')

    if case == 'All':
        # Group by manager and calculate statistics for all cases
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

        # Reorder columns
        columns_order = [
            'manager', 'total_drivers', 'matched_drivers', 'unmatched_drivers', 'matched_percentage',
            'avg_distance', 'median_distance', 'min_distance', 'max_distance'
        ]
        manager_stats = manager_stats[columns_order]
    else:
        # Group by manager and calculate statistics for the specified case
        manager_stats = df[df['exchange_location'] == case].groupby('manager').agg(
            count=('exchange_location', 'count'),
            matched_count=('is_matched', 'sum'),
            avg_distance=('distance', lambda x: round(x.mean() / 1000, 2)),
            median_distance=('distance', lambda x: round(x.median() / 1000, 2)),
            min_distance=('distance', lambda x: round(x.min() / 1000, 2)),
            max_distance=('distance', lambda x: round(x.max() / 1000, 2))
        ).reset_index()

        manager_stats['matched_percentage'] = round(manager_stats['matched_count'] / manager_stats['count'] * 100, 2)
        manager_stats = manager_stats.merge(total_drivers, on='manager', how='left')
        manager_stats['percentage'] = round(manager_stats['count'] / manager_stats['total_drivers'] * 100, 2)

        manager_stats = manager_stats.drop('total_drivers', axis=1)
        # manager_stats.columns = [f"{case}_{col}" if col != 'manager' else col for col in manager_stats.columns]

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
    # Define blocks
    vehicle_shifts['block_0'] = (vehicle_shifts[['Mañana', 'Tarde', 'Turno_Completo', 'TP-V-D', 'TP-L-V', 'L-J', 'L-J_(40h)']].sum(axis=1) == 0)
    vehicle_shifts['block_1'] = (vehicle_shifts['Turno_Completo'] == 1)
    vehicle_shifts['block_2'] = (vehicle_shifts['Tarde'] == 1)
    vehicle_shifts['block_3'] = ((vehicle_shifts['L-J'] + vehicle_shifts['L-J_(40h)'] + vehicle_shifts['Mañana'] + vehicle_shifts['TP-L-V'] + vehicle_shifts['TP-V-D']) >= 1) & (vehicle_shifts['Tarde'] == 0) & (vehicle_shifts['Turno_Completo'] == 0)

    ## Define holes in each block ##
    # Block 0: All vehicles in block_0 are holes
    vehicle_shifts['hole_block_0'] = vehicle_shifts['block_0']

    # Block 1: No holes in block_1
    vehicle_shifts['hole_block_1'] = False

    # Block 2: Holes in block_2 if number_of_drivers < 2 and not in 'Mañana'
    vehicle_shifts['hole_block_2'] = (
        (vehicle_shifts['block_2'] == 1) &
        (vehicle_shifts['Mañana'] == 0) &
        (vehicle_shifts['number_of_drivers'] < 2))

    # Block 3: Holes in block_3 if number_of_drivers < 3
    vehicle_shifts['hole_block_3'] = (
        (vehicle_shifts['block_3'] == 1) &
        (vehicle_shifts['number_of_drivers'] < 3))

    # Combine the holes from all blocks
    vehicle_shifts['hole'] = (
        vehicle_shifts['hole_block_0'] |
        vehicle_shifts['hole_block_1'] |
        vehicle_shifts['hole_block_2'] |
        vehicle_shifts['hole_block_3'])
    
    # Init hole counts
    holes = vehicle_shifts[vehicle_shifts['hole'] == True]
    hole_counts = pd.DataFrame(columns=[ 'plate', 'manager', 'center', 'Mañana', 'Tarde', 'L-J_(40h)', 'TP-V-D'])

    grouped_holes_df = holes.groupby(['plate', 'manager', 'center'])
    for (plate, manager, center), group in grouped_holes_df:
        hole_counts.loc[len(hole_counts)] = [plate, manager, center, 0, 0, 0, 0]
    
        for _, row in group.iterrows():
            if row['block_0'] == True:
                hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'Mañana'] += 1
                hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'L-J_(40h)'] += 1
                hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'TP-V-D'] += 1
            elif row['block_1'] == True:
                pass
            elif row['block_2'] == True:
                hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'Mañana'] += 1
            elif row['block_3'] == True:
                if row['Mañana'] == 0 and row['TP-L-V'] == 0:
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'Mañana'] += 1
                if row['L-J'] == 0 and row['L-J_(40h)'] == 0:
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'L-J_(40h)'] += 1
                if row['TP-V-D'] == 0:
                    hole_counts.loc[(hole_counts['plate'] == plate) & (hole_counts['center'] == center) & (hole_counts['manager'] == manager), 'TP-V-D'] += 1

    total_by_manager_df = hole_counts.groupby(['manager', 'center']).sum().reset_index()
    total_by_manager_df['total'] = total_by_manager_df[['Mañana', 'Tarde', 'L-J_(40h)', 'TP-V-D']].sum(axis=1)
    total_by_manager_df.drop(columns=['plate'], inplace=True)

    return total_by_manager_df

