-- auth.users 作成時に apl.user_profile を自動作成するトリガー
-- signUp と user_profile を同一トランザクションで管理し、整合性を保証する
-- 参照: docs/for_cursorAI/web/ユーザー登録画面仕様.md

-- トリガー関数（SECURITY DEFINER で RLS を bypass）
create or replace function apl.handle_new_user_profile()
returns trigger language plpgsql security definer set search_path = apl
as $$
declare
  v_name text := trim(coalesce(new.raw_user_meta_data->>'display_name', ''));
  v_role text := coalesce(nullif(trim(new.raw_user_meta_data->>'role'), ''), 'USER');
begin
  if v_name = '' then
    raise exception 'display_name is required';
  end if;
  insert into apl.user_profile (id, name, role)
  values (new.id, v_name, v_role);
  return new;
end;
$$;

-- トリガー登録
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute procedure apl.handle_new_user_profile();
