import sqlite3
import logging
from database.connection import db
from typing import Optional, List, Dict
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS

logger = logging.getLogger(__name__)

class TournamentService:
    
    @staticmethod
    def create_tournament_with_levels(name: str, date: str, location: str, format_info: str, 
                         entry_fee: str, description: str, created_by: int, 
                         tournament_type: str = 'single',
                         level_restriction: str = 'open',
                         min_level: str = None,
                         max_level: str = None) -> Optional[int]:
        """Создать турнир с ограничениями по уровню"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tournaments (name, date, location, format_info, entry_fee, 
                                           description, created_by, tournament_type,
                                           level_restriction, min_level, max_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, date, location, format_info, entry_fee, description, created_by, 
                      tournament_type, level_restriction, min_level, max_level))
                
                new_tournament_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Tournament created with levels: {name} (ID: {new_tournament_id}), restriction: {level_restriction}, range: {min_level}-{max_level}")
                return new_tournament_id
        except Exception as e:
            logger.error(f"Error creating tournament with levels: {e}")
            return None
    
    @staticmethod
    def get_all_tournaments() -> List[Dict]:
        """Получить все турниры"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, date, location, format_info, entry_fee, description, status, created_at
                    FROM tournaments WHERE status = 'active'
                    ORDER BY date ASC
                """)
                
                results = cursor.fetchall()
                tournaments = []
                
                for row in results:
                    tournaments.append({
                        'id': row[0],
                        'name': row[1],
                        'date': row[2],
                        'location': row[3],
                        'format_info': row[4],
                        'entry_fee': row[5],
                        'description': row[6],
                        'status': row[7],
                        'created_at': row[8]
                    })
                
                return tournaments
        except Exception as e:
            logger.error(f"Error getting tournaments: {e}")
            return []
    
    @staticmethod
    def get_tournament_by_id(tournament_id: int) -> Optional[Dict]:
        """Получить турнир по ID"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, date, location, format_info, entry_fee, description, 
                           status, created_at, level_restriction, min_level, max_level
                    FROM tournaments WHERE id = ?
                """, (tournament_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'name': result[1],
                        'date': result[2],
                        'location': result[3],
                        'format_info': result[4],
                        'entry_fee': result[5],
                        'description': result[6],
                        'status': result[7],
                        'created_at': result[8],
                        'level_restriction': result[9],  # ← ДОБАВИЛИ
                        'min_level': result[10],         # ← ДОБАВИЛИ
                        'max_level': result[11]          # ← ДОБАВИЛИ
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting tournament: {e}")
            return None
            
    @staticmethod
    def archive_tournament(tournament_id: int) -> bool:
        """Переместить турнир в архив"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tournaments 
                    SET status = 'archived'
                    WHERE id = ?
                """, (tournament_id,))
                
                conn.commit()
                logger.info(f"Tournament {tournament_id} archived")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error archiving tournament: {e}")
            return False
            
    @staticmethod
    def update_tournament(tournament_id: int, updated_fields: dict) -> bool:
        """Обновить поля турнира"""
        try:
            # Соответствие полей формы и базы данных
            field_mapping = {
                'name': 'name',
                'date': 'date', 
                'location': 'location',
                'format': 'format_info',
                'entry_fee': 'entry_fee',
                'description': 'description'
            }
            
            set_clauses = []
            values = []
            
            for field, value in updated_fields.items():
                db_field = field_mapping.get(field)
                if db_field:
                    set_clauses.append(f"{db_field} = ?")
                    values.append(value)
            
            if not set_clauses:
                logger.warning("No valid fields to update")
                return False
            
            values.append(tournament_id)
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                query = f"UPDATE tournaments SET {', '.join(set_clauses)} WHERE id = ?"
                
                logger.info(f"Executing query: {query}")
                logger.info(f"With values: {values}")
                
                cursor.execute(query, values)
                conn.commit()
                
                rows_affected = cursor.rowcount
                logger.info(f"Rows affected: {rows_affected}")
                
                return rows_affected > 0
                
        except Exception as e:
            logger.error(f"Error updating tournament: {e}")
            return False