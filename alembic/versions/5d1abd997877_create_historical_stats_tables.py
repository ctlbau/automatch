"""Create VehicleShiftHistorical and ManagerStatsHistorical tables

Revision ID: 5d1abd997877
Revises: c489041f33b3
Create Date: 2024-04-23 18:08:31.203548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '5d1abd997877'
down_revision: Union[str, None] = 'c489041f33b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    tables = insp.get_table_names()
    if 'VehicleShiftsHistorical' not in tables:
        op.create_table('VehicleShiftsHistorical',
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('plate', sa.String(10), nullable=False),
        sa.Column('manager', sa.String(50), nullable=False),
        sa.Column('center', sa.String(70), nullable=True),
        sa.Column('number_of_drivers', sa.Integer, nullable=False),
        sa.Column('manana', sa.Integer, nullable=False),
        sa.Column('tarde', sa.Integer, nullable=False),
        sa.Column('tp_v_d', sa.Integer, nullable=False),
        sa.Column('tp_l_v', sa.Integer, nullable=False),
        sa.Column('l_j', sa.Integer, nullable=False),
        sa.Column('l_j_40h', sa.Integer, nullable=False),
        sa.Column('turno_completo', sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(['plate'], ['Vehicles.plate'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['manager'], ['Managers.name'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['center'], ['Centers.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plate', 'date')
        )
    
    if 'ManagerStatsHistorical' not in tables:
        op.create_table('ManagerStatsHistorical',
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('manager', sa.String(50), nullable=False),
        sa.Column('total_drivers', sa.Integer, nullable=True),
        sa.Column('matched_drivers', sa.Integer, nullable=True),
        sa.Column('unmatched_drivers', sa.Integer, nullable=True),
        sa.Column('matched_percentage', sa.Float, nullable=True),
        sa.Column('avg_distance', sa.Float, nullable=True),
        sa.Column('median_distance', sa.Float, nullable=True),
        sa.Column('min_distance', sa.Float, nullable=True),
        sa.Column('max_distance', sa.Float, nullable=True),
        sa.Column('exchange_location', sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(['manager'], ['Managers.name'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('date', 'manager', 'exchange_location')
        )

def downgrade() -> None:
    op.drop_table('VehicleShiftsHistorical')
    op.drop_table('ManagerStatsHistorical')
