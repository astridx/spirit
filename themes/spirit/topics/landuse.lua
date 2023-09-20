-- ---------------------------------------------------------------------------
--
-- Theme: spirit
-- Topic: landuse
--
-- ---------------------------------------------------------------------------

local common = require ('themes.spirit.common')

local themepark, theme, cfg = ...

themepark:add_table{
    name = 'landuse',
    ids_type = 'area',
    geom = 'multipolygon',
    columns = themepark:columns({
        { column = 'name', type = 'text' },
        { column = 'landuse', type = 'text' },
        { column = 'way_area', type = 'real' },
        { column = 'point', type = 'point' },
    }),
    indexes = {
        { method = 'gist', column = 'point' },
    }
}

themepark:add_proc('area', function(object, data)
    local landuse
    if object.tags.landuse == 'residential' then
        landuse = 'residential'
    elseif object.tags.natural == 'commercial' then
        landuse = 'commercial'
    elseif object.tags.natural == 'retail' then
        landuse = 'retail'
    elseif object.tags.natural == 'industrial' then
        landuse = 'industrial'
    end

    if landuse ~= nil and common.isarea(object.tags) then
        local g_transform = object:as_area():transform(3857)
        local a = {
            name = object.tags.name,
            landuse = landuse,
            way_area = g_transform:area(),
            geom = g_transform }

        if object.tags.name then
            a.point = g_transform:pole_of_inaccessibility()
        end
        themepark:add_debug_info(a, object.tags)
        themepark:insert('landuse', a)
    end
end)
