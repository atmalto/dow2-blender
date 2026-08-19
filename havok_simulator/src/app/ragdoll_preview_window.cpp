#include "ragdoll_preview_window.h"

#include <QLabel>
#include <QSplitter>
#include <QTabWidget>
#include <QTreeWidget>
#include <QTreeWidgetItem>
#include <QTreeWidgetItemIterator>
#include <QVBoxLayout>
#include <QWidget>

#include "ragdoll_preview_viewport.h"

namespace
{
    const int kBoneIndexRole = Qt::UserRole;

    void configure_bone_tree(QTreeWidget* tree, const char* header_label)
    {
        if (!tree)
        {
            return;
        }

        tree->setHeaderLabel(header_label);
        tree->setUniformRowHeights(true);
        tree->setAlternatingRowColors(false);
    }

    void build_bone_tree(QTreeWidget* tree, const std::vector<RagdollPreviewBone>& bones)
    {
        std::vector<QTreeWidgetItem*> items;

        if (!tree)
        {
            return;
        }

        tree->clear();
        items.resize(bones.size(), static_cast<QTreeWidgetItem*>(0));

        for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
        {
            const RagdollPreviewBone& bone = bones[bone_index];
            QTreeWidgetItem* item = new QTreeWidgetItem();
            QString label = QString::fromLocal8Bit(bone.name.c_str());

            if (bone.parent_index < 0)
            {
                label += " (root)";
            }

            item->setText(0, label);
            item->setData(0, kBoneIndexRole, bone.bone_index);
            items[bone_index] = item;
        }

        for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
        {
            const RagdollPreviewBone& bone = bones[bone_index];
            QTreeWidgetItem* item = items[bone_index];

            if (!item)
            {
                continue;
            }

            if (bone.parent_index >= 0 && bone.parent_index < static_cast<int>(items.size()) && items[bone.parent_index])
            {
                items[bone.parent_index]->addChild(item);
            }
            else
            {
                tree->addTopLevelItem(item);
            }
        }

        tree->expandAll();
    }

    QString skeleton_kind_label(RagdollPreviewSkeletonKind skeleton_kind)
    {
        return skeleton_kind == RagdollPreviewSkeletonAnimation
            ? QString("Animation Skeleton")
            : QString("Ragdoll Skeleton");
    }

    QString detail_indent()
    {
        return "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
    }

    QString section_heading(const QString& title)
    {
        return QString("<div style='margin-top:6px; margin-bottom:0px;'><span style='font-size:12pt; font-weight:600;'>%1</span></div><br/>").arg(title);
    }

    QString detail_row(const QString& label, const QString& value)
    {
        return QString("%1<b>%2:</b> <span style='color:#4f6f8f;'>%3</span><br/>")
            .arg(detail_indent())
            .arg(label)
            .arg(value);
    }

    QString vector3_text(const float value[3])
    {
        return QString("[%1, %2, %3]")
            .arg(value[0], 0, 'f', 3)
            .arg(value[1], 0, 'f', 3)
            .arg(value[2], 0, 'f', 3);
    }

    QString quaternion_text(const float value[4])
    {
        return QString("[%1, %2, %3, %4]")
            .arg(value[0], 0, 'f', 3)
            .arg(value[1], 0, 'f', 3)
            .arg(value[2], 0, 'f', 3)
            .arg(value[3], 0, 'f', 3);
    }

    QString radians_to_degrees_text(float value)
    {
        return QString::number(value * 57.2957795f, 'f', 3);
    }
}

RagdollPreviewWindow::RagdollPreviewWindow(QWidget* parent)
    : QMainWindow(parent, Qt::Window)
    , m_viewport(0)
    , m_skeleton_tabs(0)
    , m_animation_bone_tree(0)
    , m_ragdoll_bone_tree(0)
    , m_summary_label(0)
    , m_details_label(0)
    , m_selected_bone_index(-1)
    , m_active_skeleton_kind(RagdollPreviewSkeletonAnimation)
{
    QWidget* content = new QWidget(this);
    QVBoxLayout* content_layout = new QVBoxLayout(content);
    QSplitter* splitter = new QSplitter(Qt::Horizontal, content);
    QWidget* summary_panel = new QWidget(splitter);
    QVBoxLayout* summary_layout = new QVBoxLayout(summary_panel);

    setWindowTitle("Ragdoll Preview");
    resize(1180, 760);

    m_skeleton_tabs = new QTabWidget(splitter);
    m_animation_bone_tree = new QTreeWidget(m_skeleton_tabs);
    m_ragdoll_bone_tree = new QTreeWidget(m_skeleton_tabs);
    configure_bone_tree(m_animation_bone_tree, "Animation Skeleton");
    configure_bone_tree(m_ragdoll_bone_tree, "Ragdoll Skeleton");
    m_skeleton_tabs->addTab(m_animation_bone_tree, "Animation Skeleton");
    m_skeleton_tabs->addTab(m_ragdoll_bone_tree, "Ragdoll Skeleton");

    m_viewport = new RagdollPreviewViewport(splitter);

    m_summary_label = new QLabel(summary_panel);
    m_summary_label->setWordWrap(true);
    m_summary_label->setAlignment(Qt::AlignTop | Qt::AlignLeft);
    m_summary_label->setTextFormat(Qt::RichText);

    m_details_label = new QLabel(summary_panel);
    m_details_label->setWordWrap(true);
    m_details_label->setAlignment(Qt::AlignTop | Qt::AlignLeft);
    m_details_label->setTextFormat(Qt::RichText);

    m_skeleton_tabs->setMinimumWidth(240);
    summary_panel->setMinimumWidth(320);
    summary_layout->setSpacing(12);
    splitter->setChildrenCollapsible(false);
    splitter->setHandleWidth(8);

    summary_layout->addWidget(m_summary_label);
    summary_layout->addWidget(m_details_label);
    summary_layout->addStretch(1);
    summary_panel->setLayout(summary_layout);

    splitter->addWidget(m_skeleton_tabs);
    splitter->addWidget(m_viewport);
    splitter->addWidget(summary_panel);
    splitter->setStretchFactor(0, 0);
    splitter->setStretchFactor(1, 1);
    splitter->setStretchFactor(2, 0);

    content_layout->addWidget(splitter);
    content->setLayout(content_layout);
    setCentralWidget(content);

    connect(m_animation_bone_tree, SIGNAL(itemSelectionChanged()), this, SLOT(bone_tree_selection_changed()));
    connect(m_ragdoll_bone_tree, SIGNAL(itemSelectionChanged()), this, SLOT(bone_tree_selection_changed()));
    connect(m_skeleton_tabs, SIGNAL(currentChanged(int)), this, SLOT(skeleton_tab_changed(int)));
    connect(m_viewport, SIGNAL(bone_selected(int)), this, SLOT(viewport_bone_selected(int)));

    clear_preview_data();
}

QTreeWidget* RagdollPreviewWindow::active_bone_tree() const
{
    return m_active_skeleton_kind == RagdollPreviewSkeletonAnimation
        ? m_animation_bone_tree
        : m_ragdoll_bone_tree;
}

const std::vector<RagdollPreviewBone>& RagdollPreviewWindow::active_bones() const
{
    return m_active_skeleton_kind == RagdollPreviewSkeletonAnimation
        ? m_preview_data.animation_bones
        : m_preview_data.bones;
}

void RagdollPreviewWindow::set_preview_data(const RagdollPreviewData& preview_data)
{
    const int previous_bone_index = m_selected_bone_index;
    const RagdollPreviewSkeletonKind previous_skeleton_kind = m_active_skeleton_kind;

    m_preview_data = preview_data;
    rebuild_bone_trees();

    if (!m_preview_data.animation_bones.empty())
    {
        m_active_skeleton_kind = previous_skeleton_kind == RagdollPreviewSkeletonRagdoll
            ? RagdollPreviewSkeletonRagdoll
            : RagdollPreviewSkeletonAnimation;
    }
    else
    {
        m_active_skeleton_kind = RagdollPreviewSkeletonRagdoll;
    }

    if (m_skeleton_tabs)
    {
        m_skeleton_tabs->blockSignals(true);
        m_skeleton_tabs->setCurrentIndex(m_active_skeleton_kind == RagdollPreviewSkeletonAnimation ? 0 : 1);
        m_skeleton_tabs->setTabEnabled(0, !m_preview_data.animation_bones.empty());
        m_skeleton_tabs->blockSignals(false);
    }

    m_viewport->set_preview_data(preview_data);
    m_viewport->set_active_skeleton_kind(m_active_skeleton_kind);
    refresh_summary();

    if (previous_bone_index >= 0 && previous_bone_index < static_cast<int>(active_bones().size()))
    {
        select_bone(previous_bone_index, false);
        sync_tree_selection_to_bone(previous_bone_index);
    }
    else
    {
        if (m_animation_bone_tree)
        {
            m_animation_bone_tree->blockSignals(true);
            m_animation_bone_tree->clearSelection();
            m_animation_bone_tree->setCurrentItem(0);
            m_animation_bone_tree->blockSignals(false);
        }
        if (m_ragdoll_bone_tree)
        {
            m_ragdoll_bone_tree->blockSignals(true);
            m_ragdoll_bone_tree->clearSelection();
            m_ragdoll_bone_tree->setCurrentItem(0);
            m_ragdoll_bone_tree->blockSignals(false);
        }
        m_selected_bone_index = -1;
        m_viewport->set_selected_bone_index(-1);
        refresh_details();
    }
}

void RagdollPreviewWindow::clear_preview_data()
{
    m_preview_data = RagdollPreviewData();
    m_selected_bone_index = -1;
    m_active_skeleton_kind = RagdollPreviewSkeletonAnimation;
    if (m_animation_bone_tree)
    {
        m_animation_bone_tree->clear();
    }
    if (m_ragdoll_bone_tree)
    {
        m_ragdoll_bone_tree->clear();
    }
    if (m_skeleton_tabs)
    {
        m_skeleton_tabs->blockSignals(true);
        m_skeleton_tabs->setCurrentIndex(0);
        m_skeleton_tabs->setTabEnabled(0, false);
        m_skeleton_tabs->setTabEnabled(1, true);
        m_skeleton_tabs->blockSignals(false);
    }
    if (m_summary_label)
    {
        m_summary_label->setText("No ragdoll preview loaded.");
    }
    if (m_details_label)
    {
        m_details_label->setText("<span style='font-size:11pt; font-weight:600;'>Selection</span><br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#4f6f8f;'>No bone selected.</span>");
    }
    if (m_viewport)
    {
        m_viewport->clear_preview_data();
    }
    setWindowTitle("Ragdoll Preview");
}

SceneEntityId RagdollPreviewWindow::entity_id() const
{
    return m_preview_data.entity_id;
}

void RagdollPreviewWindow::bone_tree_selection_changed()
{
    QTreeWidget* tree = active_bone_tree();
    QTreeWidgetItem* current_item = tree ? tree->currentItem() : 0;
    if (!current_item)
    {
        select_bone(-1, false);
        return;
    }

    select_bone(current_item->data(0, kBoneIndexRole).toInt(), false);
}

void RagdollPreviewWindow::skeleton_tab_changed(int index)
{
    m_active_skeleton_kind = index == 0
        ? RagdollPreviewSkeletonAnimation
        : RagdollPreviewSkeletonRagdoll;

    if (m_viewport)
    {
        m_viewport->set_active_skeleton_kind(m_active_skeleton_kind);
        m_viewport->set_selected_bone_index(-1);
    }

    if (m_animation_bone_tree)
    {
        m_animation_bone_tree->blockSignals(true);
        m_animation_bone_tree->clearSelection();
        m_animation_bone_tree->setCurrentItem(0);
        m_animation_bone_tree->blockSignals(false);
    }

    if (m_ragdoll_bone_tree)
    {
        m_ragdoll_bone_tree->blockSignals(true);
        m_ragdoll_bone_tree->clearSelection();
        m_ragdoll_bone_tree->setCurrentItem(0);
        m_ragdoll_bone_tree->blockSignals(false);
    }

    m_selected_bone_index = -1;
    refresh_summary();
    refresh_details();
}

void RagdollPreviewWindow::viewport_bone_selected(int bone_index)
{
    select_bone(bone_index, true);
}

void RagdollPreviewWindow::select_bone(int bone_index, bool from_viewport)
{
    const std::vector<RagdollPreviewBone>& bones = active_bones();

    if (bone_index < 0 || bone_index >= static_cast<int>(bones.size()))
    {
        m_selected_bone_index = -1;
        if (m_viewport)
        {
            m_viewport->set_selected_bone_index(-1);
        }
        refresh_details();
        return;
    }

    m_selected_bone_index = bone_index;
    if (m_viewport)
    {
        m_viewport->set_selected_bone_index(bone_index);
    }
    if (from_viewport)
    {
        sync_tree_selection_to_bone(bone_index);
    }
    refresh_details();
}

void RagdollPreviewWindow::sync_tree_selection_to_bone(int bone_index)
{
    QTreeWidget* tree = active_bone_tree();
    QTreeWidgetItemIterator iterator(tree);

    if (!tree)
    {
        return;
    }

    while (*iterator)
    {
        QTreeWidgetItem* item = *iterator;
        if (item->data(0, kBoneIndexRole).toInt() == bone_index)
        {
            tree->blockSignals(true);
            tree->setCurrentItem(item);
            item->setSelected(true);
            tree->scrollToItem(item);
            tree->blockSignals(false);
            return;
        }
        ++iterator;
    }
}

void RagdollPreviewWindow::refresh_details()
{
    QString details;

    const std::vector<RagdollPreviewBone>& bones = active_bones();
    const bool is_animation_view = m_active_skeleton_kind == RagdollPreviewSkeletonAnimation;

    if (m_selected_bone_index < 0 || m_selected_bone_index >= static_cast<int>(bones.size()))
    {
        if (m_details_label)
        {
            m_details_label->setText("<span style='font-size:11pt; font-weight:600;'>Selection</span><br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#4f6f8f;'>Select a tree node or click a preview bone.</span>");
        }
        return;
    }

    const RagdollPreviewBone& bone = bones[m_selected_bone_index];

    details += section_heading("Bone");
    details += detail_row("Name", QString::fromLocal8Bit(bone.name.c_str()));
    details += detail_row("Index", QString::number(bone.bone_index));
    details += detail_row("Parent", QString::number(bone.parent_index));
    details += detail_row("Translation", vector3_text(bone.translation));
    details += detail_row("Rotation", quaternion_text(bone.rotation));
    details += detail_row("Scale", vector3_text(bone.scale));

    details += section_heading("Body");
    if (is_animation_view)
    {
        details += detail_row("State", "not part of animation skeleton preview");
    }
    else
    {
        const RagdollPreviewBody& body = m_preview_data.bodies[m_selected_bone_index];

        if (!body.is_present)
        {
            details += detail_row("State", "not present");
        }
        else
        {
            details += detail_row("Name", QString::fromLocal8Bit(body.name.c_str()));
            details += detail_row("Shape", ragdoll_preview_body_shape_label(body.shape_type));
            details += detail_row("Mass", QString::number(body.mass, 'f', 3));
            details += detail_row("Friction", QString::number(body.friction, 'f', 3));
            details += detail_row("Restitution", QString::number(body.restitution, 'f', 3));
            details += detail_row("Motion", ragdoll_preview_motion_type_label(body.motion_type));
            details += detail_row("Linear Damping", QString::number(body.linear_damping, 'f', 3));
            details += detail_row("Angular Damping", QString::number(body.angular_damping, 'f', 3));
            details += detail_row("Filter", QString::number(body.collision_filter_info));
            details += detail_row("Quality", QString::number(body.quality_type));
            details += detail_row("Position", vector3_text(body.position));
            details += detail_row("Rotation", quaternion_text(body.rotation));

            if (body.shape_type == RagdollPreviewBodyShapeCapsule)
            {
                details += detail_row("Radius", QString::number(body.radius, 'f', 3));
                details += detail_row("Vertex A", vector3_text(body.capsule_vertices));
                details += detail_row("Vertex B", vector3_text(body.capsule_vertices + 3));
            }
            else if (body.shape_type == RagdollPreviewBodyShapeBox)
            {
                details += detail_row("Half Extents", vector3_text(body.half_extents));
            }
            else if (body.shape_type == RagdollPreviewBodyShapeSphere)
            {
                details += detail_row("Radius", QString::number(body.radius, 'f', 3));
            }
        }
    }

    details += section_heading("Joint"); // render joint details only for ragdoll skeleton view since animation skeleton not relevant to ragdoll joint properties
    if (is_animation_view)
    {
        details += detail_row("State", "not part of animation skeleton preview");
    }
    else
    {
        const RagdollPreviewJoint& joint = m_preview_data.joints[m_selected_bone_index];

        if (!joint.is_present)
        {
            details += detail_row("State", "not present");
        }
        else
        {
            details += detail_row("Name", QString::fromLocal8Bit(joint.name.c_str()));
            details += detail_row("Constraint", ragdoll_preview_constraint_type_label(joint.constraint_type));
            details += detail_row("Parent Bone", QString::number(joint.parent_bone_index));
            details += detail_row("Child Bone", QString::number(joint.bone_index));
            details += detail_row("Pivot A", vector3_text(joint.pivot_a));
            details += detail_row("Pivot B", vector3_text(joint.pivot_b));
            details += detail_row("Twist Axis A", vector3_text(joint.twist_axis_a));
            details += detail_row("Twist Axis B", vector3_text(joint.twist_axis_b));
            details += detail_row("Plane Axis A", vector3_text(joint.plane_axis_a));
            details += detail_row("Plane Axis B", vector3_text(joint.plane_axis_b));
            details += detail_row("Twist Min", radians_to_degrees_text(joint.twist_min_radians) + " deg");
            details += detail_row("Twist Max", radians_to_degrees_text(joint.twist_max_radians) + " deg");
            details += detail_row("Cone", radians_to_degrees_text(joint.cone_angle_radians) + " deg");
            details += detail_row("Plane Min", radians_to_degrees_text(joint.plane_min_radians) + " deg");
            details += detail_row("Plane Max", radians_to_degrees_text(joint.plane_max_radians) + " deg");
            details += detail_row("Hinge Min", radians_to_degrees_text(joint.hinge_min_radians) + " deg");
            details += detail_row("Hinge Max", radians_to_degrees_text(joint.hinge_max_radians) + " deg");
            details += detail_row("Friction Torque", QString::number(joint.friction_torque, 'f', 3));
        }
    }

    if (m_details_label)
    {
        m_details_label->setText(details);
    }
}

void RagdollPreviewWindow::rebuild_bone_trees()
{
    build_bone_tree(m_animation_bone_tree, m_preview_data.animation_bones);
    build_bone_tree(m_ragdoll_bone_tree, m_preview_data.bones);
}

void RagdollPreviewWindow::refresh_summary()
{
    int body_count = 0;
    int joint_count = 0;

    for (std::size_t body_index = 0; body_index < m_preview_data.bodies.size(); ++body_index)
    {
        if (m_preview_data.bodies[body_index].is_present)
        {
            ++body_count;
        }
    }

    for (std::size_t joint_index = 0; joint_index < m_preview_data.joints.size(); ++joint_index)
    {
        if (m_preview_data.joints[joint_index].is_present)
        {
            ++joint_count;
        }
    }

    if (m_summary_label)
    {
        QString summary;
        const QString active_name = m_active_skeleton_kind == RagdollPreviewSkeletonAnimation
            ? QString::fromLocal8Bit(m_preview_data.animation_skeleton_name.c_str())
            : QString::fromLocal8Bit(m_preview_data.skeleton_name.c_str());

        summary += section_heading("Asset");
        summary += detail_row("Path", QString::fromLocal8Bit(m_preview_data.asset_path.c_str()));
        summary += section_heading("Currently previewing:");
        summary += detail_row("Active", skeleton_kind_label(m_active_skeleton_kind));
        summary += detail_row("Bones", QString::number(static_cast<int>(active_bones().size())));
        summary += detail_row("Ragdoll Bones", QString::number(static_cast<int>(m_preview_data.bones.size())));
        summary += detail_row("Bodies", QString::number(body_count));
        summary += detail_row("Joints", QString::number(joint_count));
        m_summary_label->setText(summary);
    }

    setWindowTitle(QString("Ragdoll Preview - %1").arg(skeleton_kind_label(m_active_skeleton_kind)));
}