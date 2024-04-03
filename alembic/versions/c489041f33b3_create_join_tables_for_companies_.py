"""Create join tables for companies_centers and drivers_vehicles_exchange_locations

Revision ID: c489041f33b3
Revises: 27308421a3f8
Create Date: 2024-04-03 13:25:22.467795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c489041f33b3'
down_revision: Union[str, None] = '27308421a3f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('CompaniesCenters',
                    sa.Column('company_id', sa.Integer, nullable=False),
                    sa.Column('center_id', sa.Integer, nullable=False),
                    sa.PrimaryKeyConstraint('company_id', 'center_id'),
                    sa.ForeignKeyConstraint(['company_id'], ['Companies.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['center_id'], ['Centers.id'], ondelete='CASCADE')
                    )
    op.create_table('DriversVehiclesExchangeLocations',
                    sa.Column('driver_id', sa.Integer, nullable=False),
                    sa.Column('vehicle_id', sa.Integer, nullable=False),
                    sa.Column('exchange_location_id', sa.Integer, nullable=True),
                    sa.PrimaryKeyConstraint('driver_id', 'vehicle_id', 'exchange_location_id'),
                    sa.ForeignKeyConstraint(['driver_id'], ['Drivers.kendra_id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['vehicle_id'], ['Vehicles.kendra_id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['exchange_location_id'], ['ExchangeLocations.id'])
                    )

def downgrade() -> None:
    op.drop_table('DriversVehiclesExchangeLocations')
    op.drop_table('CompaniesCenters')
