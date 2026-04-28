package com.claudeflow.repository;

import com.claudeflow.entity.PhaseStepEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 阶段步骤Repository
 */
@Repository
public interface PhaseStepRepository extends JpaRepository<PhaseStepEntity, String> {

    /**
     * 按任务ID和阶段查询步骤列表（按索引排序）
     */
    List<PhaseStepEntity> findByTaskIdAndPhaseOrderByStepIndex(String taskId, String phase);

    /**
     * 按任务ID查询所有步骤
     */
    List<PhaseStepEntity> findByTaskIdOrderByPhaseAscStepIndexAsc(String taskId);

    /**
     * 按任务ID删除所有步骤
     */
    void deleteByTaskId(String taskId);
}