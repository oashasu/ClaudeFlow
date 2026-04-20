package com.claudeflow.repository;

import com.claudeflow.entity.TaskEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 任务Repository
 */
@Repository
public interface TaskRepository extends JpaRepository<TaskEntity, String> {

    /**
     * 按状态查询任务
     */
    List<TaskEntity> findByStatus(String status);

    /**
     * 按状态列表查询
     */
    List<TaskEntity> findByStatusIn(List<String> statuses);

    /**
     * 统计各状态任务数量
     */
    @Query("SELECT t.status, COUNT(t) FROM TaskEntity t GROUP BY t.status")
    List<Object[]> countByStatus();

    /**
     * 查询需要清理的任务
     */
    @Query("SELECT t FROM TaskEntity t WHERE t.status IN :statuses AND t.gmtModified < :threshold")
    List<TaskEntity> findForCleanup(List<String> statuses, LocalDateTime threshold);

    /**
     * 删除需要清理的任务
     */
    void deleteByStatusInAndGmtModifiedBefore(List<String> statuses, LocalDateTime threshold);
}