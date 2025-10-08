import sqlite3
import logging
from database.connection import db
from typing import Optional, List, Dict
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS

logger = logging.getLogger(__name__)

class ParticipationService:
    
    @staticmethod
    def get_participants_count(tournament_id: int) -> Dict[str, int]:
        """Получить количество участников турнира"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Считаем confirmed + pending как занятые места
                cursor.execute("""
                    SELECT COUNT(*) FROM participations 
                    WHERE tournament_id = ? AND status IN ('confirmed', 'pending')
                """, (tournament_id,))
                
                total_count = cursor.fetchone()[0]
                
                main_count = min(total_count, MAX_MAIN_PARTICIPANTS)
                reserve_count = max(0, total_count - MAX_MAIN_PARTICIPANTS)
                
                return {
                    'total': total_count,
                    'main': main_count,
                    'reserve': reserve_count,
                    'available_main': MAX_MAIN_PARTICIPANTS - main_count,
                    'available_reserve': MAX_RESERVE_PARTICIPANTS - reserve_count
                }
        except Exception as e:
            logger.error(f"Error getting participants count: {e}")
            return {'total': 0, 'main': 0, 'reserve': 0, 'available_main': 16, 'available_reserve': 5}
    
    @staticmethod
    def add_participant(user_id: int, tournament_id: int) -> bool:
        """Добавить участника в турнир"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли свободные места
                counts = ParticipationService.get_participants_count(tournament_id)
                total_available = counts['available_main'] + counts['available_reserve']
                
                if total_available <= 0:
                    return False
                
                cursor.execute("""
                    INSERT INTO participations (user_id, tournament_id, status)
                    VALUES (?, ?, 'confirmed')
                """, (user_id, tournament_id))
                
                conn.commit()
                logger.info(f"User {user_id} added to tournament {tournament_id}")
                return True
        except sqlite3.IntegrityError:
            # Пользователь уже зарегистрирован
            logger.warning(f"User {user_id} already registered for tournament {tournament_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
            return False
    
    @staticmethod
    def remove_participant(user_id: int, tournament_id: int) -> bool:
        """Удалить участника из турнира"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM participations 
                    WHERE user_id = ? AND tournament_id = ?
                """, (user_id, tournament_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing participant: {e}")
            return False
    
    @staticmethod
    def is_user_registered(user_id: int, tournament_id: int) -> bool:
        """Проверить, зарегистрирован ли пользователь на турнир"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM participations 
                    WHERE user_id = ? AND tournament_id = ?
                """, (user_id, tournament_id))
                
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Error checking user registration: {e}")
            return False
    
    @staticmethod
    def get_tournament_participants(tournament_id: int) -> List[Dict]:
        """Получить список участников турнира с цветовой индикацией"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.full_name, u.phone_number, p.registration_time, p.status
                    FROM participations p
                    JOIN users u ON p.user_id = u.telegram_id
                    WHERE p.tournament_id = ?
                    ORDER BY p.registration_time ASC
                """, (tournament_id,))
                
                results = cursor.fetchall()
                participants = []
                
                for i, row in enumerate(results, 1):
                    participant_type = "основной" if i <= MAX_MAIN_PARTICIPANTS else "резерв"
                    
                    # Определяем цветовую индикацию
                    if row[3] == 'confirmed':
                        status_icon = "🟢"  # Зеленый - подтверждено
                        status_text = "одобрено"
                    else:  # pending
                        status_icon = "🟡"  # Желтый - ожидает
                        status_text = "ожидает"
                    
                    participants.append({
                        'position': i,
                        'name': row[0],
                        'phone': row[1],
                        'registration_time': row[2],
                        'status': row[3],
                        'type': participant_type,
                        'status_icon': status_icon,
                        'status_text': status_text
                    })
                
                return participants
        except Exception as e:
            logger.error(f"Error getting tournament participants: {e}")
            return []

    @staticmethod
    def add_participant_pending(user_id: int, tournament_id: int) -> bool:
        """Добавить участника со статусом pending"""
        try:
            from datetime import datetime, timedelta
            from config import PAYMENT_TIMEOUT_MINUTES
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли свободные места (включая pending)
                cursor.execute("""
                    SELECT COUNT(*) FROM participations 
                    WHERE tournament_id = ? AND status IN ('confirmed', 'pending')
                """, (tournament_id,))
                
                current_count = cursor.fetchone()[0]
                max_total = MAX_MAIN_PARTICIPANTS + MAX_RESERVE_PARTICIPANTS
                
                if current_count >= max_total:
                    return False
                
                # Устанавливаем дедлайн
                deadline = datetime.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
                
                cursor.execute("""
                    INSERT INTO participations (user_id, tournament_id, status, payment_deadline)
                    VALUES (?, ?, 'pending', ?)
                """, (user_id, tournament_id, deadline))
                
                conn.commit()
                logger.info(f"User {user_id} added to tournament {tournament_id} as pending")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already registered for tournament {tournament_id}")
            return False
        except Exception as e:
            logger.error(f"Error adding pending participant: {e}")
            return False

    @staticmethod
    def get_pending_participations(tournament_id: int) -> List[Dict]:
        """Получить участников со статусом pending для админа"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.id, u.full_name, u.phone_number, p.registration_time, p.payment_deadline
                    FROM participations p
                    JOIN users u ON p.user_id = u.telegram_id
                    WHERE p.tournament_id = ? AND p.status = 'pending'
                    ORDER BY p.registration_time ASC
                """, (tournament_id,))
                
                results = cursor.fetchall()
                participants = []
                
                for row in results:
                    participants.append({
                        'participation_id': row[0],
                        'name': row[1],
                        'phone': row[2],
                        'registration_time': row[3],
                        'payment_deadline': row[4]
                    })
                
                return participants
        except Exception as e:
            logger.error(f"Error getting pending participations: {e}")
            return []

    @staticmethod
    def approve_participation(participation_id: int) -> bool:
        """Одобрить участие"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE participations 
                    SET status = 'confirmed', payment_deadline = NULL
                    WHERE id = ?
                """, (participation_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error approving participation: {e}")
            return False

    @staticmethod
    def reject_participation(participation_id: int) -> bool:
        """Отклонить участие"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM participations WHERE id = ?
                """, (participation_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error rejecting participation: {e}")
            return False

    @staticmethod
    def cleanup_expired_participations():
        """Удалить просроченные заявки"""
        try:
            from datetime import datetime
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM participations 
                    WHERE status = 'pending' AND payment_deadline < ?
                """, (datetime.now(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired participations")
                
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning expired participations: {e}")
            return 0
            
    @staticmethod
    def get_user_participation_status(user_id: int, tournament_id: int) -> Optional[Dict]:
        """Получить статус участия конкретного пользователя"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT status, payment_deadline, registration_time
                    FROM participations 
                    WHERE user_id = ? AND tournament_id = ?
                """, (user_id, tournament_id))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'status': result[0],
                        'payment_deadline': result[1],
                        'registration_time': result[2]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user participation status: {e}")
            return None