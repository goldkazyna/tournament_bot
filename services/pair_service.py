import sqlite3
import logging
from database.connection import db
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from config import MAX_PAIR_SLOTS, MAX_PAIR_RESERVE, PAYMENT_TIMEOUT_MINUTES

logger = logging.getLogger(__name__)

class PairService:
    
    @staticmethod
    def get_pairs_count(tournament_id: int) -> Dict[str, int]:
        """Получить количество пар в турнире"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Считаем confirmed + pending пары
                cursor.execute("""
                    SELECT COUNT(*) FROM pairs 
                    WHERE tournament_id = ? AND status IN ('confirmed', 'pending')
                """, (tournament_id,))
                
                total_pairs = cursor.fetchone()[0]
                
                main_pairs = min(total_pairs, MAX_PAIR_SLOTS)
                reserve_pairs = max(0, total_pairs - MAX_PAIR_SLOTS)
                
                return {
                    'total': total_pairs,
                    'main': main_pairs,
                    'reserve': reserve_pairs,
                    'available_main': MAX_PAIR_SLOTS - main_pairs,
                    'available_reserve': MAX_PAIR_RESERVE - reserve_pairs
                }
        except Exception as e:
            logger.error(f"Error getting pairs count: {e}")
            return {'total': 0, 'main': 0, 'reserve': 0, 'available_main': MAX_PAIR_SLOTS, 'available_reserve': MAX_PAIR_RESERVE}
    
    @staticmethod
    def is_user_in_pair(user_id: int, tournament_id: int) -> bool:
        """Проверить, участвует ли пользователь в паре на этом турнире"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM pairs 
                    WHERE tournament_id = ? AND (player1_id = ? OR player2_id = ?)
                """, (tournament_id, user_id, user_id))
                
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Error checking user in pair: {e}")
            return False
    
    @staticmethod
    def create_pair(tournament_id: int, player1_id: int, player2_id: int) -> bool:
        """Создать пару для турнира"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли свободные места
                counts = PairService.get_pairs_count(tournament_id)
                total_available = counts['available_main'] + counts['available_reserve']
                
                if total_available <= 0:
                    logger.warning(f"No slots available for tournament {tournament_id}")
                    return False
                
                # Проверяем что оба игрока не в других парах
                if PairService.is_user_in_pair(player1_id, tournament_id):
                    logger.warning(f"Player {player1_id} already in pair for tournament {tournament_id}")
                    return False
                
                if PairService.is_user_in_pair(player2_id, tournament_id):
                    logger.warning(f"Player {player2_id} already in pair for tournament {tournament_id}")
                    return False
                
                # Определяем номер пары
                cursor.execute("""
                    SELECT COUNT(*) FROM pairs 
                    WHERE tournament_id = ? AND status IN ('confirmed', 'pending')
                """, (tournament_id,))
                pair_number = cursor.fetchone()[0] + 1
                
                # Устанавливаем дедлайн
                deadline = datetime.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
                
                cursor.execute("""
                    INSERT INTO pairs (tournament_id, player1_id, player2_id, pair_number, status, payment_deadline)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                """, (tournament_id, player1_id, player2_id, pair_number, deadline))
                
                conn.commit()
                logger.info(f"Pair created: {player1_id} + {player2_id} for tournament {tournament_id}")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error creating pair: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating pair: {e}")
            return False
    
    @staticmethod
    def remove_pair(player_id: int, tournament_id: int) -> bool:
        """Удалить пару (оба игрока) из турнира по ID любого из игроков"""
        try:
            logger.warning(f"🔵 Removing pair: player_id={player_id}, tournament_id={tournament_id}")
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Находим пару где player_id это либо player1, либо player2
                cursor.execute("""
                    DELETE FROM pairs 
                    WHERE tournament_id = ? 
                    AND (player1_id = ? OR player2_id = ?)
                """, (tournament_id, player_id, player_id))
                
                deleted_rows = cursor.rowcount
                conn.commit()
                
                logger.warning(f"🔵 Deleted {deleted_rows} rows")
                
                return deleted_rows > 0
        except Exception as e:
            logger.error(f"Error removing pair: {e}")
            return False
    
    @staticmethod
    def get_tournament_pairs(tournament_id: int) -> List[Dict]:
        """Получить список пар турнира"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.id, p.player1_id, p.player2_id, p.pair_number, p.status,
                           p.registration_time, p.payment_deadline,
                           u1.full_name as player1_name, u1.phone_number as player1_phone,
                           u2.full_name as player2_name, u2.phone_number as player2_phone
                    FROM pairs p
                    JOIN users u1 ON p.player1_id = u1.telegram_id
                    JOIN users u2 ON p.player2_id = u2.telegram_id
                    WHERE p.tournament_id = ?
                    ORDER BY p.registration_time ASC
                """, (tournament_id,))
                
                results = cursor.fetchall()
                pairs = []
                
                for row in results:
                    pair_type = "основная" if row[3] <= MAX_PAIR_SLOTS else "резерв"
                    
                    # Определяем цветовую индикацию
                    if row[4] == 'confirmed':
                        status_icon = "🟢"
                        status_text = "одобрено"
                    else:  # pending
                        status_icon = "🟡"
                        status_text = "ожидает"
                    
                    pairs.append({
                        'pair_id': row[0],
                        'player1_id': row[1],
                        'player2_id': row[2],
                        'pair_number': row[3],
                        'status': row[4],
                        'registration_time': row[5],
                        'payment_deadline': row[6],
                        'player1_name': row[7],
                        'player1_phone': row[8],
                        'player2_name': row[9],
                        'player2_phone': row[10],
                        'type': pair_type,
                        'status_icon': status_icon,
                        'status_text': status_text
                    })
                
                return pairs
        except Exception as e:
            logger.error(f"Error getting tournament pairs: {e}")
            return []
    
    @staticmethod
    def get_user_pair(user_id: int, tournament_id: int) -> Optional[Dict]:
        """Получить пару пользователя на турнире"""
        try:
            pairs = PairService.get_tournament_pairs(tournament_id)
            for pair in pairs:
                if pair['player1_id'] == user_id or pair['player2_id'] == user_id:
                    return pair
            return None
        except Exception as e:
            logger.error(f"Error getting user pair: {e}")
            return None
    
    @staticmethod
    def approve_pair(pair_id: int) -> bool:
        """Одобрить пару"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pairs 
                    SET status = 'confirmed', payment_deadline = NULL
                    WHERE id = ?
                """, (pair_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error approving pair: {e}")
            return False
    
    @staticmethod
    def reject_pair(pair_id: int) -> bool:
        """Отклонить пару"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM pairs WHERE id = ?
                """, (pair_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error rejecting pair: {e}")
            return False