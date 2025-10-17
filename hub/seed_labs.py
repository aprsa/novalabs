"""
Seed script to populate labs for galaxy explorer progression

Creates 15 labs across 3 categories:
- Earth (labs 0-4): Celestial Navigation, Seasons, Moon Phases, Eclipses, Tides
- Solar System (labs 5-9): Kepler's Laws, Roemer's Delay, Planets, Asteroids, Exoplanets
- Stars (labs 10-14): Parallax, HR Diagram, PHOEBE, Spectroscopy, Stellar Evolution
"""
import json
from sqlmodel import SQLModel, Session, select
from .database import engine
from .models import Lab


# Lab definitions with sequence and prerequisites
LABS = [
    # ===== EARTH CATEGORY (0-4) =====
    {
        'ref': 'celestial-navigation',
        'name': 'Celestial Navigation',
        'description': 'Learn to navigate using stars and celestial coordinates. '
                       'Understand right ascension, declination, and altitude-azimuth systems.',
        'ui_url': 'http://localhost:8201',
        'api_url': 'http://localhost:8201/api',
        'session_manager_url': 'http://localhost:8201/sessions',
        'sequence_order': 0,
        'category': 'Earth',
        'prerequisite_refs': [],
        'has_bonus_challenge': True,
        'max_bonus_points': 10.0
    },
    {
        'ref': 'seasons',
        'name': 'Seasons and Earth\'s Tilt',
        'description': 'Explore why Earth has seasons. Understand axial tilt, '
                       'solstices, and equinoxes.',
        'ui_url': 'http://localhost:8202',
        'api_url': 'http://localhost:8202/api',
        'session_manager_url': 'http://localhost:8202/sessions',
        'sequence_order': 1,
        'category': 'Earth',
        'prerequisite_refs': ['celestial-navigation'],
        'has_bonus_challenge': False,
        'max_bonus_points': 0.0
    },
    {
        'ref': 'moon-phases',
        'name': 'Moon Phases',
        'description': 'Track the lunar cycle and understand why the Moon shows different '
                       'phases throughout the month.',
        'ui_url': 'http://localhost:8203',
        'api_url': 'http://localhost:8203/api',
        'session_manager_url': 'http://localhost:8203/sessions',
        'sequence_order': 2,
        'category': 'Earth',
        'prerequisite_refs': ['seasons'],
        'has_bonus_challenge': True,
        'max_bonus_points': 5.0
    },
    {
        'ref': 'eclipses',
        'name': 'Solar and Lunar Eclipses',
        'description': 'Predict and understand eclipses. Learn about Saros cycles and '
                       'eclipse seasons.',
        'ui_url': 'http://localhost:8204',
        'api_url': 'http://localhost:8204/api',
        'session_manager_url': 'http://localhost:8204/sessions',
        'sequence_order': 3,
        'category': 'Earth',
        'prerequisite_refs': ['moon-phases'],
        'has_bonus_challenge': True,
        'max_bonus_points': 10.0
    },
    {
        'ref': 'tides',
        'name': 'Tides and Tidal Forces',
        'description': 'Understand how the Moon and Sun create tides on Earth. '
                       'Explore spring and neap tides.',
        'ui_url': 'http://localhost:8205',
        'api_url': 'http://localhost:8205/api',
        'session_manager_url': 'http://localhost:8205/sessions',
        'sequence_order': 4,
        'category': 'Earth',
        'prerequisite_refs': ['eclipses'],
        'has_bonus_challenge': False,
        'max_bonus_points': 0.0
    },

    # ===== SOLAR SYSTEM CATEGORY (5-9) =====
    {
        'ref': 'keplers-laws',
        'name': 'Kepler\'s Laws of Planetary Motion',
        'description': 'Discover the laws that govern planetary orbits. Calculate orbital '
                       'periods and distances.',
        'ui_url': 'http://localhost:8206',
        'api_url': 'http://localhost:8206/api',
        'session_manager_url': 'http://localhost:8206/sessions',
        'sequence_order': 5,
        'category': 'Solar System',
        'prerequisite_refs': ['tides'],
        'has_bonus_challenge': True,
        'max_bonus_points': 15.0
    },
    {
        'ref': 'roemers-delay',
        'name': 'Roemer\'s Speed of Light',
        'description': 'Measure the speed of light using Jupiter\'s moons, just like '
                       'Ole Rømer did in 1676.',
        'ui_url': 'http://localhost:8207',
        'api_url': 'http://localhost:8207/api',
        'session_manager_url': 'http://localhost:8207/sessions',
        'sequence_order': 6,
        'category': 'Solar System',
        'prerequisite_refs': ['keplers-laws'],
        'has_bonus_challenge': True,
        'max_bonus_points': 10.0
    },
    {
        'ref': 'planets',
        'name': 'Planetary Properties',
        'description': 'Compare the physical and orbital properties of planets in our '
                       'solar system.',
        'ui_url': 'http://localhost:8208',
        'api_url': 'http://localhost:8208/api',
        'session_manager_url': 'http://localhost:8208/sessions',
        'sequence_order': 7,
        'category': 'Solar System',
        'prerequisite_refs': ['roemers-delay'],
        'has_bonus_challenge': False,
        'max_bonus_points': 0.0
    },
    {
        'ref': 'asteroids',
        'name': 'Asteroids and Near-Earth Objects',
        'description': 'Track asteroids and understand their orbits. Assess impact risks.',
        'ui_url': 'http://localhost:8209',
        'api_url': 'http://localhost:8209/api',
        'session_manager_url': 'http://localhost:8209/sessions',
        'sequence_order': 8,
        'category': 'Solar System',
        'prerequisite_refs': ['planets'],
        'has_bonus_challenge': True,
        'max_bonus_points': 5.0
    },
    {
        'ref': 'exoplanets',
        'name': 'Exoplanet Detection',
        'description': 'Discover planets around other stars using transit and radial '
                       'velocity methods.',
        'ui_url': 'http://localhost:8210',
        'api_url': 'http://localhost:8210/api',
        'session_manager_url': 'http://localhost:8210/sessions',
        'sequence_order': 9,
        'category': 'Solar System',
        'prerequisite_refs': ['asteroids'],
        'has_bonus_challenge': True,
        'max_bonus_points': 20.0
    },

    # ===== STARS CATEGORY (10-14) =====
    {
        'ref': 'parallax',
        'name': 'Stellar Parallax and Distance',
        'description': 'Measure distances to nearby stars using parallax. Understand '
                       'the parsec.',
        'ui_url': 'http://localhost:8211',
        'api_url': 'http://localhost:8211/api',
        'session_manager_url': 'http://localhost:8211/sessions',
        'sequence_order': 10,
        'category': 'Stars',
        'prerequisite_refs': ['exoplanets'],
        'has_bonus_challenge': True,
        'max_bonus_points': 10.0
    },
    {
        'ref': 'hr-diagram',
        'name': 'Hertzsprung-Russell Diagram',
        'description': 'Plot stars on the HR diagram and understand stellar classification. '
                       'Explore main sequence, giants, and dwarfs.',
        'ui_url': 'http://localhost:8212',
        'api_url': 'http://localhost:8212/api',
        'session_manager_url': 'http://localhost:8212/sessions',
        'sequence_order': 11,
        'category': 'Stars',
        'prerequisite_refs': ['parallax'],
        'has_bonus_challenge': False,
        'max_bonus_points': 0.0
    },
    {
        'ref': 'phoebe',
        'name': 'Binary Stars with PHOEBE',
        'description': 'Model eclipsing binary star systems using PHOEBE. Fit light curves '
                       'and determine stellar properties.',
        'ui_url': 'http://localhost:8213',
        'api_url': 'http://localhost:8213/api',
        'session_manager_url': 'http://localhost:8213/sessions',
        'sequence_order': 12,
        'category': 'Stars',
        'prerequisite_refs': ['hr-diagram'],
        'has_bonus_challenge': True,
        'max_bonus_points': 25.0
    },
    {
        'ref': 'spectroscopy',
        'name': 'Stellar Spectroscopy',
        'description': 'Analyze stellar spectra to determine composition, temperature, '
                       'and motion.',
        'ui_url': 'http://localhost:8214',
        'api_url': 'http://localhost:8214/api',
        'session_manager_url': 'http://localhost:8214/sessions',
        'sequence_order': 13,
        'category': 'Stars',
        'prerequisite_refs': ['phoebe'],
        'has_bonus_challenge': True,
        'max_bonus_points': 15.0
    },
    {
        'ref': 'stellar-evolution',
        'name': 'Stellar Evolution',
        'description': 'Follow the life cycle of stars from birth to death. Understand '
                       'supernovae, white dwarfs, and black holes.',
        'ui_url': 'http://localhost:8215',
        'api_url': 'http://localhost:8215/api',
        'session_manager_url': 'http://localhost:8215/sessions',
        'sequence_order': 14,
        'category': 'Stars',
        'prerequisite_refs': ['spectroscopy'],
        'has_bonus_challenge': True,
        'max_bonus_points': 20.0
    }
]


def seed_labs():
    """Populate database with lab sequence"""
    # Create tables first
    print('Creating database tables...')
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Check if labs already exist
        existing = session.exec(select(Lab)).first()
        if existing:
            print('⚠ Labs already exist in database. Skipping seed.')
            print('  To reseed, delete the database and run again.')
            return

        # Create all labs
        for lab_data in LABS:
            # Convert prerequisite_refs list to JSON string
            lab_dict = lab_data.copy()
            if 'prerequisite_refs' in lab_dict:
                lab_dict['prerequisite_refs'] = json.dumps(lab_dict['prerequisite_refs'])
            lab = Lab(**lab_dict)
            session.add(lab)

        session.commit()
        print(f'✓ Seeded {len(LABS)} labs:')
        print('  - Earth: 5 labs')
        print('  - Solar System: 5 labs')
        print('  - Stars: 5 labs')


def list_labs():
    """List all labs in sequence order"""
    with Session(engine) as session:
        labs = session.exec(select(Lab).order_by(Lab.sequence_order)).all()

        if not labs:
            print('No labs found in database.')
            return

        print(f'\n{"#":<3} {"Category":<15} {"Lab Name":<35} {"Prerequisites"}')
        print('=' * 90)

        for lab in labs:
            # Parse JSON prerequisite_refs
            prereq_list = json.loads(lab.prerequisite_refs) if lab.prerequisite_refs else []
            prereqs = ', '.join(prereq_list) if prereq_list else 'None'
            bonus = ' 🌟' if lab.has_bonus_challenge else ''
            print(f'{lab.sequence_order:<3} {lab.category:<15} {lab.name:<35}{bonus} {prereqs}')


def main():
    """Entry point for seeding/listing labs"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_labs()
    else:
        seed_labs()
        print('\nSeeding complete! Run with "list" to see all labs:')
        print('  novalabs-seed list')


if __name__ == '__main__':
    main()
