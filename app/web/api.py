from datetime import datetime
from typing import Optional

from fastapi import Query, APIRouter
from sqlalchemy import select, insert, func, and_, or_, update, desc
from starlette.responses import JSONResponse

from app.core.database import SqlSession
from app.core.snowflake_id import id_worker
from app.model.assembler import convert_vo, convert_keywrod_sqlm
from app.model.domain import sqlm_keyword, Keyword, sqlm_keyboard_switch, KeyboardSwitch
from app.model.vo import MksVO, KeywordVO

api_router = APIRouter(prefix='/api')

@api_router.get('/mkslist')
async def mkslist(draw: Optional[int]=None, start: Optional[int]=0, length: Optional[int]=10, search: str=Query(alias='s', default=None)):
    with SqlSession() as session:
        stmt_list = select(sqlm_keyboard_switch).offset(start).limit(length).order_by(desc(sqlm_keyboard_switch.columns.update_time))
        stmt_count = select(func.count(sqlm_keyboard_switch.columns.id))
        if search is not None:
            s = '%' + search + '%'
            search_expression = and_(
                or_(
                    sqlm_keyboard_switch.columns.name.like(s),
                    sqlm_keyboard_switch.columns.studio.like(s),
                    sqlm_keyboard_switch.columns.manufacturer.like(s),
                    sqlm_keyboard_switch.columns.tag.like(s)
                )
            )
            stmt_list = stmt_list.where(search_expression)
            stmt_count = stmt_count.where(search_expression)
        list = session.fetchall(stmt_list, KeyboardSwitch)
        mkslist = [convert_vo(i) for i in list]
        total = session.count(stmt_count)
    return {'draw': draw, 'page_list': mkslist, 'recordsTotal': total, 'recordsFiltered': total}

@api_router.post('/mks', response_class=JSONResponse)
async def save_mks(req: MksVO):
    now = datetime.now().timestamp()
    id = req.id
    is_update = True
    if req.id == '':
        is_update = False
        id = id_worker.next_id()
    keyboard_switch = KeyboardSwitch(
        name=req.name, studio=req.studio, manufacturer=req.manufacturer, type=req.type,
        pic=req.pic, tag=req.tag, quantity=req.quantity, price=req.price, desc=req.desc,
        specs=req.specs.json(),
        create_time=now, update_time=now, id=id, stash=req.stash
    )
    if keyboard_switch.studio == '':
        return {'status': 'error', 'msg': '工作室为空'}
    with SqlSession() as session:
        kw = session.fetchone(
            select(sqlm_keyword)
                .where(sqlm_keyword.columns.word==keyboard_switch.studio,
                       sqlm_keyword.columns.type=='studio'),
            Keyword
        )
        if kw is None:
            row = session.execute(
                insert(sqlm_keyword).values(Keyword(word=keyboard_switch.studio, type='studio', rank=0, deleted=0,
                                                    create_time=now, update_time=now).dict())
            )
        _ks = session.fetchone(
            select(sqlm_keyboard_switch)
                .where(sqlm_keyboard_switch.columns.name == keyboard_switch.name),
            KeyboardSwitch
        )
        if is_update:
            if _ks is not None and _ks.id != keyboard_switch.id:
                return {'status': 'error', 'msg': '轴体名字重复'}
            else:
                session.execute(
                    update(sqlm_keyboard_switch).values(manufacturer=keyboard_switch.manufacturer,
                                                        studio=keyboard_switch.studio,
                                                        pic=keyboard_switch.pic,
                                                        type=keyboard_switch.type,
                                                        tag=keyboard_switch.tag,
                                                        specs=keyboard_switch.specs,
                                                        quantity=keyboard_switch.quantity,
                                                        price=keyboard_switch.price,
                                                        desc=keyboard_switch.desc,
                                                        update_time=keyboard_switch.update_time,
                                                        name=keyboard_switch.name,
                                                        stash=keyboard_switch.stash)
                        .where(sqlm_keyboard_switch.columns.id == id)
                )
                return {'status': 'ok'}
        else:
            if _ks is None:
                session.execute(insert(sqlm_keyboard_switch).values(keyboard_switch.dict()))
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'msg': '轴体名字已存在!'}





@api_router.get("/keyword", response_class=JSONResponse)
async def keyword(
        draw: Optional[int]=None,
        start: Optional[int]=None,
        length: Optional[int]=None,
        search: str=Query(alias='s', default=None),
        type: str=Query(alias='t', default=None)
):
    with SqlSession() as session:
        stmt_list = select(sqlm_keyword).where(sqlm_keyword.columns.type==type, sqlm_keyword.columns.deleted==0).order_by(desc(sqlm_keyword.columns.create_time))
        stmt_count = select(func.count(sqlm_keyword.columns.word)).where(sqlm_keyword.columns.type==type, sqlm_keyword.columns.deleted==0)
        if search is not None:
            stmt_list = stmt_list.where(sqlm_keyword.columns.word.like('%' + search + '%'))
            stmt_count = stmt_count.where(sqlm_keyword.columns.word.like('%' + search + '%'))
        if start is None:
            list = session.fetchall(stmt_list, Keyword)
            return [m.word for m in list]
        else:
            list = session.fetchall(stmt_list.offset(start).limit(length), Keyword)
            total = session.count(stmt_count)
            return {'draw': draw, 'page_list': list, 'recordsTotal': total, 'recordsFiltered': total}

@api_router.post('/keyword', response_class=JSONResponse)
async def save_keyword(req: KeywordVO):
    with SqlSession() as session:
        _k = session.fetchone(
            select(sqlm_keyword)
                .where(sqlm_keyword.columns.word==req.word, sqlm_keyword.columns.type==req.type),
            Keyword
        )
        if _k is None:
            dd = convert_keywrod_sqlm(req).dict()
            session.execute(insert(sqlm_keyword).values(dd))
            return {'status': 'ok'}
        else:
            now = int(datetime.now().timestamp())
            session.execute(
                update(sqlm_keyword)
                    .values(rank=req.rank, update_time=now, deleted=0, memo=req.memo)
                    .where(sqlm_keyword.columns.word==req.word, sqlm_keyword.columns.type==req.type)
            )
            return {'status': 'ok'}

@api_router.delete('/keyword', response_class=JSONResponse)
async def delete_keyword(req: KeywordVO):
    with SqlSession() as session:
        session.execute(
            update(sqlm_keyword)
                .values(deleted=1)
                .where(sqlm_keyword.columns.word==req.word, sqlm_keyword.columns.type==req.type)
        )
    return {'status': 'ok'}