"""Add initial entities

Revision ID: 27308421a3f8
Revises: 
Create Date: 2024-04-02 18:33:50.596348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '27308421a3f8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    tables = insp.get_table_names()
    
    if 'Managers' not in tables:
        op.create_table('Managers',
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(50), nullable=False),
                        sa.Index('idx_managers_name', 'name'))

    if 'Shifts' not in tables:
        op.create_table('Shifts',
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(50), nullable=False))

    if 'Companies' not in tables:
        op.create_table('Companies',
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(60), nullable=False),
                        sa.Column('company_group', sa.String(20), nullable=False))

    if 'Centers' not in tables:
        op.create_table('Centers',
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(70), nullable=False),
                        sa.Index('ixd_centers_name', 'name'))

    if 'Provinces' not in tables:
        op.create_table('Provinces',
                        sa.Column('id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(70), nullable=False))

    if 'ExchangeLocations' not in tables:
        op.create_table('ExchangeLocations',
                        sa.Column('id', sa.Integer, autoincrement=True, primary_key=True),
                        sa.Column('name', sa.String(70), nullable=False, unique=True))

    if 'Drivers' not in tables:
        op.create_table('Drivers',
                        sa.Column('kendra_id', sa.Integer, primary_key=True),
                        sa.Column('name', sa.String(80), nullable=False),
                        sa.Column('street', sa.String(255), nullable=True),
                        sa.Column('city', sa.String(70), nullable=True),
                        sa.Column('country', sa.String(70), nullable=True),
                        sa.Column('zip_code', sa.String(20), nullable=True),
                        sa.Column('lat', sa.Float, nullable=True),
                        sa.Column('lng', sa.Float, nullable=True),
                        sa.Column('province_id', sa.Integer, sa.ForeignKey('Provinces.id'), nullable=True),
                        sa.Column('manager_id', sa.Integer, sa.ForeignKey('Managers.id'), nullable=True),
                        sa.Column('shift_id', sa.Integer, sa.ForeignKey('Shifts.id'), nullable=True))

    if 'Vehicles' not in tables:
        op.create_table('Vehicles',
                        sa.Column('kendra_id', sa.Integer, nullable=False),
                        sa.Column('plate', sa.String(10), nullable=False),
                        sa.Column('status', sa.String(17), nullable=False),
                        sa.Column('date', sa.Date, nullable=False),
                        sa.Column('company_id', sa.Integer, sa.ForeignKey('Companies.id'), nullable=False),
                        sa.Column('center_id', sa.Integer, sa.ForeignKey('Centers.id'), nullable=False),
                        sa.Column('manager_id', sa.Integer, sa.ForeignKey('Managers.id'), nullable=True),
                        sa.PrimaryKeyConstraint('date', 'plate'),
                        sa.Index('idx_vehicles_plate', 'plate'),
                        sa.Index('idx_kendra_id', 'kendra_id'))

def downgrade() -> None:
    op.drop_table('Vehicles')
    op.drop_table('Drivers')
    op.drop_table('ExchangeLocations')
    op.drop_table('Provinces')
    op.drop_table('Centers')
    op.drop_table('Companies')
    op.drop_table('Shifts')
    op.drop_table('Managers')
