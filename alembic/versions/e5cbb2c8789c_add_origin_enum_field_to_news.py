"""Add origin enum field to news

Revision ID: e5cbb2c8789c
Revises: c1317d24b7dd
Create Date: 2025-07-11 23:12:11.266438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6dd73afe49b'
down_revision: Union[str, Sequence[str], None] = 'c1317d24b7dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

origin_enum = sa.Enum(
    'native', 'CTS', 'TSSDNews', 'CTWant', 'TaiwanNews', 'TTV', 'CTINews', 
    'HongKongFreePress', 'MingPaoNews', 'SingTaoDaily', 'SCMP', 
    'ChineseNewYorkTimes', 'DeutscheWelle', 'HKFreePress', 'WenWeiPo',
    'OrientalDailyNews', 'TaKungPao', 'HK01', 'InitiumMedia', 'YahooNews', 
    'HKCD', 'TheEpochTimes', 'NowTV', 'ChineseBBC', 'VOC', 'HKCourtNews', 
    'ICable', 'HKGovernmentNews', 'OrangeNews', 'TheStandard', 'HKEJ', 
    'HKET', 'RTHK', 'TheWitness', 'InMediaHK', 'PeopleDaily', 
    'XinhuaNewsAgency', 'GlobalTimes', 'CCTV', 'UnitedDailyNews', 
    'LibertyTimesNet', 'ChinaTimes', 'CNA', 'TaiwanEconomicTimes', 
    'PTSNews', 'CTEE', 'MyPeopleVol', 'TaiwanTimes', 'ChinaDailyNews', 
    'SETN', 'NextAppleNews', 'MirrorMedia', 'NowNews', 'StormMedia', 
    'TVBS', 'EBCNews', 'ETtoday', 'NewTalk', 'FTV',
    name='originenum'
)



def upgrade() -> None:
    # 1. Create the ENUM type in the database
    origin_enum.create(op.get_bind())

    # 2. Alter the existing column with explicit USING CAST
    op.execute("""
        ALTER TABLE news
        ALTER COLUMN origin
        TYPE originenum
        USING origin::originenum
    """)



def downgrade() -> None:
    # 1. Change column back to VARCHAR
    op.alter_column('news', 'origin',
        existing_type=sa.Enum(name='originenum'),
        type_=sa.VARCHAR(),
        existing_nullable=True
    )

    # 2. Drop the ENUM type
    origin_enum.drop(op.get_bind())