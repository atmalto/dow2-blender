#include "scene_persistence.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QString>
#include <QXmlStreamReader>
#include <QXmlStreamWriter>

namespace
{
    const int kSceneFileVersion = 1;

    QString to_string(float value)
    {
        return QString::number(value, 'f', 6);
    }

    float read_float_attribute(const QXmlStreamAttributes& attributes, const char* name, float default_value)
    {
        bool ok = false;
        const QString value = attributes.value(QLatin1String(name)).toString();
        const float parsed = value.toFloat(&ok);
        return ok ? parsed : default_value;
    }

    int read_int_attribute(const QXmlStreamAttributes& attributes, const char* name, int default_value)
    {
        bool ok = false;
        const QString value = attributes.value(QLatin1String(name)).toString();
        const int parsed = value.toInt(&ok);
        return ok ? parsed : default_value;
    }

    bool read_bool_attribute(const QXmlStreamAttributes& attributes, const char* name, bool default_value)
    {
        const QString value = attributes.value(QLatin1String(name)).toString().trimmed().toLower();
        if (value == QLatin1String("1") || value == QLatin1String("true") || value == QLatin1String("yes"))
        {
            return true;
        }
        if (value == QLatin1String("0") || value == QLatin1String("false") || value == QLatin1String("no"))
        {
            return false;
        }
        return default_value;
    }

    QString make_stored_path(const QString& scene_file_path, const QString& referenced_path)
    {
        const QFileInfo referenced_info(referenced_path);
        if (!referenced_info.exists())
        {
            return referenced_path;
        }

        const QDir scene_dir = QFileInfo(scene_file_path).absoluteDir();
        return scene_dir.relativeFilePath(referenced_info.absoluteFilePath());
    }

    QString resolve_stored_path(const QString& scene_file_path, const QString& stored_path)
    {
        const QFileInfo stored_info(stored_path);
        if (stored_info.isAbsolute())
        {
            return QDir::cleanPath(stored_info.absoluteFilePath());
        }

        const QDir scene_dir = QFileInfo(scene_file_path).absoluteDir();
        return QDir::cleanPath(scene_dir.absoluteFilePath(stored_path));
    }

    void write_object(QXmlStreamWriter& xml, const PersistedSceneObject& object)
    {
        xml.writeStartElement("object");
        xml.writeAttribute("name", QString::fromLocal8Bit(object.name.c_str()));
        xml.writeAttribute("editable", object.editable ? "1" : "0");
        xml.writeAttribute("object_type", QString::number(object.spec.object_type));
        xml.writeAttribute("body_type", QString::number(object.spec.body_type));
        xml.writeAttribute("position_x", to_string(object.spec.position[0]));
        xml.writeAttribute("position_y", to_string(object.spec.position[1]));
        xml.writeAttribute("position_z", to_string(object.spec.position[2]));
        xml.writeAttribute("rotation_x", to_string(object.spec.rotation_degrees[0]));
        xml.writeAttribute("rotation_y", to_string(object.spec.rotation_degrees[1]));
        xml.writeAttribute("rotation_z", to_string(object.spec.rotation_degrees[2]));
        xml.writeAttribute("scale_x", to_string(object.spec.scale[0]));
        xml.writeAttribute("scale_y", to_string(object.spec.scale[1]));
        xml.writeAttribute("scale_z", to_string(object.spec.scale[2]));
        xml.writeAttribute("restitution", to_string(object.spec.restitution));
        xml.writeAttribute("mass", to_string(object.spec.mass));
        xml.writeAttribute("shape_radius", to_string(object.spec.shape_radius));

        if (!object.spec.convex_hull_vertices.empty())
        {
            std::size_t vertex_index = 0;
            xml.writeStartElement("convex_hull");
            for (vertex_index = 0; vertex_index < object.spec.convex_hull_vertices.size(); ++vertex_index)
            {
                const ConvexHullVertex& vertex = object.spec.convex_hull_vertices[vertex_index];
                xml.writeStartElement("vertex");
                xml.writeAttribute("x", to_string(vertex.x));
                xml.writeAttribute("y", to_string(vertex.y));
                xml.writeAttribute("z", to_string(vertex.z));
                xml.writeEndElement();
            }
            xml.writeEndElement();
        }

        xml.writeEndElement();
    }

    void write_force(QXmlStreamWriter& xml, const PersistedSceneForce& force)
    {
        xml.writeStartElement("force");
        xml.writeAttribute("name", QString::fromLocal8Bit(force.name.c_str()));
        xml.writeAttribute("position_x", to_string(force.spec.position[0]));
        xml.writeAttribute("position_y", to_string(force.spec.position[1]));
        xml.writeAttribute("position_z", to_string(force.spec.position[2]));
        xml.writeAttribute("rotation_x", to_string(force.spec.rotation_degrees[0]));
        xml.writeAttribute("rotation_y", to_string(force.spec.rotation_degrees[1]));
        xml.writeAttribute("rotation_z", to_string(force.spec.rotation_degrees[2]));
        xml.writeAttribute("strength", to_string(force.spec.strength));
        xml.writeAttribute("mode", QString::number(force.spec.mode));
        xml.writeAttribute("active", force.spec.active ? "1" : "0");
        xml.writeAttribute("radius", to_string(force.spec.radius));
        xml.writeEndElement();
    }
}

bool save_scene_file(
    const char* output_file,
    const PersistedSceneData& scene,
    std::string* error_message)
{
    QFile file(QString::fromLocal8Bit(output_file));
    QXmlStreamWriter xml(&file);
    std::size_t ragdoll_index = 0;
    std::size_t object_index = 0;
    std::size_t force_index = 0;

    if (!file.open(QIODevice::WriteOnly | QIODevice::Text | QIODevice::Truncate))
    {
        if (error_message)
        {
            *error_message = QString("Could not open scene file for writing: %1").arg(file.fileName()).toLocal8Bit().constData();
        }
        return false;
    }

    xml.setAutoFormatting(true);
    xml.writeStartDocument();
    xml.writeStartElement("havok_scene");
    xml.writeAttribute("version", QString::number(kSceneFileVersion));

    xml.writeStartElement("ragdolls");
    for (ragdoll_index = 0; ragdoll_index < scene.ragdolls.size(); ++ragdoll_index)
    {
        const PersistedSceneRagdoll& ragdoll = scene.ragdolls[ragdoll_index];
        xml.writeStartElement("ragdoll");
        xml.writeAttribute("name", QString::fromLocal8Bit(ragdoll.name.c_str()));
        xml.writeAttribute(
            "asset_path",
            make_stored_path(file.fileName(), QString::fromLocal8Bit(ragdoll.spec.asset_path.c_str())));
        xml.writeAttribute("position_x", to_string(ragdoll.spec.position[0]));
        xml.writeAttribute("position_y", to_string(ragdoll.spec.position[1]));
        xml.writeAttribute("position_z", to_string(ragdoll.spec.position[2]));
        xml.writeEndElement();
    }
    xml.writeEndElement();

    xml.writeStartElement("objects");
    for (object_index = 0; object_index < scene.objects.size(); ++object_index)
    {
        write_object(xml, scene.objects[object_index]);
    }
    xml.writeEndElement();

    xml.writeStartElement("forces");
    for (force_index = 0; force_index < scene.forces.size(); ++force_index)
    {
        write_force(xml, scene.forces[force_index]);
    }
    xml.writeEndElement();

    xml.writeEndElement();
    xml.writeEndDocument();

    if (xml.hasError())
    {
        if (error_message)
        {
            *error_message = "Failed while writing the scene file.";
        }
        return false;
    }

    return true;
}

bool load_scene_file(
    const char* input_file,
    PersistedSceneData* scene,
    std::vector<std::string>* warnings,
    std::string* error_message)
{
    QFile file(QString::fromLocal8Bit(input_file));
    QXmlStreamReader xml(&file);

    if (!scene)
    {
        return false;
    }

    *scene = PersistedSceneData();

    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
    {
        if (error_message)
        {
            *error_message = QString("Could not open scene file: %1").arg(file.fileName()).toLocal8Bit().constData();
        }
        return false;
    }

    if (!xml.readNextStartElement() || xml.name() != QLatin1String("havok_scene"))
    {
        if (error_message)
        {
            *error_message = "The selected file is not a Havok Scene App scene file.";
        }
        return false;
    }

    scene->version = read_int_attribute(xml.attributes(), "version", 0);
    if (scene->version != kSceneFileVersion)
    {
        if (error_message)
        {
            *error_message = "Unsupported scene file version.";
        }
        return false;
    }

    while (xml.readNextStartElement())
    {
        if (xml.name() == QLatin1String("ragdolls"))
        {
            while (xml.readNextStartElement())
            {
                if (xml.name() == QLatin1String("ragdoll"))
                {
                    PersistedSceneRagdoll ragdoll;
                    const QXmlStreamAttributes attributes = xml.attributes();
                    const QString stored_path = attributes.value("asset_path").toString();
                    const QString resolved_path = resolve_stored_path(file.fileName(), stored_path);

                    ragdoll.name = attributes.value("name").toString().toLocal8Bit().constData();
                    ragdoll.spec.asset_path = resolved_path.toLocal8Bit().constData();
                    ragdoll.spec.position[0] = read_float_attribute(attributes, "position_x", 0.0f);
                    ragdoll.spec.position[1] = read_float_attribute(attributes, "position_y", 0.0f);
                    ragdoll.spec.position[2] = read_float_attribute(attributes, "position_z", 0.0f);

                    if (!QFileInfo(resolved_path).exists())
                    {
                        if (warnings)
                        {
                            warnings->push_back(QString("Skipped ragdoll '%1' because the referenced HKX file is missing: %2")
                                .arg(QString::fromLocal8Bit(ragdoll.name.c_str()))
                                .arg(resolved_path)
                                .toLocal8Bit().constData());
                        }
                    }
                    else
                    {
                        scene->ragdolls.push_back(ragdoll);
                    }

                    xml.skipCurrentElement();
                }
                else
                {
                    xml.skipCurrentElement();
                }
            }
        }
        else if (xml.name() == QLatin1String("objects"))
        {
            while (xml.readNextStartElement())
            {
                if (xml.name() == QLatin1String("object"))
                {
                    PersistedSceneObject object;
                    const QXmlStreamAttributes attributes = xml.attributes();

                    object.name = attributes.value("name").toString().toLocal8Bit().constData();
                    object.editable = read_bool_attribute(attributes, "editable", true);
                    object.spec.object_type = read_int_attribute(attributes, "object_type", 0);
                    object.spec.body_type = read_int_attribute(attributes, "body_type", 0);
                    object.spec.position[0] = read_float_attribute(attributes, "position_x", 0.0f);
                    object.spec.position[1] = read_float_attribute(attributes, "position_y", 0.0f);
                    object.spec.position[2] = read_float_attribute(attributes, "position_z", 0.0f);
                    object.spec.rotation_degrees[0] = read_float_attribute(attributes, "rotation_x", 0.0f);
                    object.spec.rotation_degrees[1] = read_float_attribute(attributes, "rotation_y", 0.0f);
                    object.spec.rotation_degrees[2] = read_float_attribute(attributes, "rotation_z", 0.0f);
                    object.spec.scale[0] = read_float_attribute(attributes, "scale_x", 1.0f);
                    object.spec.scale[1] = read_float_attribute(attributes, "scale_y", 1.0f);
                    object.spec.scale[2] = read_float_attribute(attributes, "scale_z", 1.0f);
                    object.spec.restitution = read_float_attribute(attributes, "restitution", 0.4f);
                    object.spec.mass = read_float_attribute(attributes, "mass", 10.0f);
                    object.spec.shape_radius = read_float_attribute(attributes, "shape_radius", 0.05f);

                    while (xml.readNextStartElement())
                    {
                        if (xml.name() == QLatin1String("convex_hull"))
                        {
                            while (xml.readNextStartElement())
                            {
                                if (xml.name() == QLatin1String("vertex"))
                                {
                                    const QXmlStreamAttributes vertex_attributes = xml.attributes();
                                    object.spec.convex_hull_vertices.push_back(ConvexHullVertex(
                                        read_float_attribute(vertex_attributes, "x", 0.0f),
                                        read_float_attribute(vertex_attributes, "y", 0.0f),
                                        read_float_attribute(vertex_attributes, "z", 0.0f)));
                                    xml.skipCurrentElement();
                                }
                                else
                                {
                                    xml.skipCurrentElement();
                                }
                            }
                        }
                        else
                        {
                            xml.skipCurrentElement();
                        }
                    }

                    scene->objects.push_back(object);
                }
                else
                {
                    xml.skipCurrentElement();
                }
            }
        }
        else if (xml.name() == QLatin1String("forces"))
        {
            while (xml.readNextStartElement())
            {
                if (xml.name() == QLatin1String("force"))
                {
                    PersistedSceneForce force;
                    const QXmlStreamAttributes attributes = xml.attributes();

                    force.name = attributes.value("name").toString().toLocal8Bit().constData();
                    force.spec.position[0] = read_float_attribute(attributes, "position_x", 0.0f);
                    force.spec.position[1] = read_float_attribute(attributes, "position_y", 0.0f);
                    force.spec.position[2] = read_float_attribute(attributes, "position_z", 0.0f);
                    force.spec.rotation_degrees[0] = read_float_attribute(attributes, "rotation_x", 0.0f);
                    force.spec.rotation_degrees[1] = read_float_attribute(attributes, "rotation_y", 0.0f);
                    force.spec.rotation_degrees[2] = read_float_attribute(attributes, "rotation_z", 0.0f);
                    force.spec.strength = read_float_attribute(attributes, "strength", 0.0f);
                    force.spec.mode = read_int_attribute(attributes, "mode", 0);
                    force.spec.active = read_bool_attribute(attributes, "active", true);
                    force.spec.radius = read_float_attribute(attributes, "radius", 0.0f);

                    scene->forces.push_back(force);
                    xml.skipCurrentElement();
                }
                else
                {
                    xml.skipCurrentElement();
                }
            }
        }
        else
        {
            xml.skipCurrentElement();
        }
    }

    if (xml.hasError())
    {
        if (error_message)
        {
            *error_message = QString("Scene parse failed: %1").arg(xml.errorString()).toLocal8Bit().constData();
        }
        return false;
    }

    return true;
}