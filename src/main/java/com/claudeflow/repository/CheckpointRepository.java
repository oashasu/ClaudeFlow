package com.claudeflow.repository;

import com.claudeflow.entity.CheckpointEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Checkpoint Repository
 */
@Repository
public interface CheckpointRepository extends JpaRepository<CheckpointEntity, String> {

    /**
     * 按任务ID查询Checkpoint列表（按时间倒序）
     */
    List<CheckpointEntity> findByTaskIdOrderByGmtCreateDesc(String taskId);

    /**
     * 按任务ID删除所有Checkpoint
     */
    void deleteByTaskId(String taskId);
}